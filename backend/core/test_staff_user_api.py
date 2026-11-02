from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class StaffUserApiTests(APITestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="supervisor_stockflow",
            password="senha-ficticia-super-segura",
        )
        self.staff = get_user_model().objects.create_user(
            username="funcionario_existente",
            first_name="Funcionário Existente",
            password="senha-ficticia-staff-segura",
            is_staff=True,
        )
        self.url = reverse("funcionario-list-create")

    def payload(self, **overrides):
        data = {
            "nome": "Maria da Silva",
            "username": "maria.silva",
            "password": "Senha-Nova-StockFlow-2026",
            "password_confirmation": "Senha-Nova-StockFlow-2026",
        }
        data.update(overrides)
        return data

    def test_superuser_creates_active_staff_without_superuser_permission(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        usuario = get_user_model().objects.get(username="maria.silva")
        self.assertEqual(usuario.get_full_name(), "Maria da Silva")
        self.assertTrue(usuario.is_active)
        self.assertTrue(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.check_password("Senha-Nova-StockFlow-2026"))
        self.assertNotIn("password", response.data)

    def test_regular_staff_cannot_list_or_create_users(self):
        self.client.force_authenticate(self.staff)

        list_response = self.client.get(self.url)
        create_response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(get_user_model().objects.filter(username="maria.silva").exists())

    def test_list_contains_staff_but_not_superusers(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["username"] for item in response.data],
            [self.staff.username],
        )

    def test_rejects_duplicate_username_ignoring_case(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            self.url,
            self.payload(username="FUNCIONARIO_EXISTENTE"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_rejects_password_confirmation_mismatch(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            self.url,
            self.payload(password_confirmation="outra-senha-segura"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirmation", response.data)

    def test_rejects_weak_password(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            self.url,
            self.payload(password="123", password_confirmation="123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
