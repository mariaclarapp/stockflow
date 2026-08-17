from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


class SessionAuthenticationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "senha-ficticia-segura"
        cls.user = get_user_model().objects.create_user(
            username="farmaceutica_teste",
            password=cls.password,
            is_staff=True,
        )
        cls.inactive_user = get_user_model().objects.create_user(
            username="farmaceutica_inativa",
            password=cls.password,
            is_active=False,
            is_staff=True,
        )
        cls.non_staff_user = get_user_model().objects.create_user(
            username="usuario_sem_acesso_administrativo",
            password=cls.password,
        )

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf_url = reverse("auth-csrf")
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.me_url = reverse("auth-me")

    def csrf_token(self):
        response = self.client.get(self.csrf_url)
        return response, self.client.cookies["csrftoken"].value

    def login(self, username=None, password=None):
        _, csrf_token = self.csrf_token()
        return self.client.post(
            self.login_url,
            {
                "username": username or self.user.username,
                "password": password or self.password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

    def test_csrf_endpoint_sets_cookie_and_returns_token(self):
        response, cookie_token = self.csrf_token()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)
        self.assertTrue(cookie_token)

    def test_valid_login_returns_safe_user_data(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data["user"]),
            {"id", "username", "is_staff", "is_superuser"},
        )
        self.assertEqual(response.data["user"]["username"], self.user.username)
        self.assertFalse(response.data["user"]["is_superuser"])

    def test_invalid_login_uses_generic_error(self):
        response = self.login(password="senha-incorreta")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Não foi possível autenticar com as credenciais informadas.",
        )

    def test_inactive_user_cannot_login(self):
        response = self.login(username=self.inactive_user.username)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_active_non_staff_user_cannot_login(self):
        response = self.login(username=self.non_staff_user.username)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Não foi possível autenticar com as credenciais informadas.",
        )
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_creates_django_session(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.session[SESSION_KEY],
            str(self.user.pk),
        )

    def test_authenticated_user_can_access_me(self):
        self.login()

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.pk)
        self.assertTrue(response.data["is_staff"])

    def test_staff_user_can_access_administrative_endpoint(self):
        self.login()

        response = self.client.get(reverse("medicamento-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_staff_user_cannot_access_administrative_endpoints(self):
        self.client.force_login(self.non_staff_user)

        list_endpoints = [
            "subgrupo-gmus-list",
            "principio-ativo-list",
            "classificacao-list",
            "medicamento-list",
            "ups-list",
            "competencia-list",
            "lote-list",
            "estoque-list",
        ]
        for endpoint in list_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        _, csrf_token = self.csrf_token()
        upload_response = self.client.post(
            reverse("inventory-import-upload"),
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(upload_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_session_cannot_access_me_or_logout(self):
        self.client.force_login(self.non_staff_user)
        _, csrf_token = self.csrf_token()

        me_response = self.client.get(self.me_url)
        logout_response = self.client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(me_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(logout_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_anonymous_user_cannot_access_me(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_ends_current_session(self):
        self.login()
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_access_is_denied_after_logout(self):
        self.login()
        csrf_token = self.client.cookies["csrftoken"].value
        self.client.post(self.logout_url, HTTP_X_CSRFTOKEN=csrf_token)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_requires_csrf_token(self):
        self.login()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_public_medicine_endpoint_remains_anonymous(self):
        response = self.client.get(reverse("public-medicamento-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_endpoint_remains_protected(self):
        response = self.client.get(reverse("medicamento-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
