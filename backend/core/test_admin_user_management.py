from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Competencia, Ups
from importacoes.models import Importacao


class DjangoAdminUserManagementTests(TestCase):
    password = "senha-ficticia-segura"

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.superuser = user_model.objects.create_superuser(
            username="administrador_sistema",
            password=cls.password,
        )
        cls.staff = user_model.objects.create_user(
            username="farmaceutica_staff",
            password=cls.password,
            is_staff=True,
        )

    def setUp(self):
        self.client = Client()

    def login_admin(self):
        self.client.force_login(self.superuser)

    def update_user_via_admin(self, user, **changes):
        data = {
            "username": user.username,
            "password": user.password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": "on" if user.is_active else "",
            "is_staff": "on" if user.is_staff else "",
            "is_superuser": "on" if user.is_superuser else "",
            "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
            "_save": "Salvar",
        }
        for field, value in changes.items():
            data[field] = "on" if value is True else "" if value is False else value

        return self.client.post(
            reverse("admin:auth_user_change", args=[user.pk]),
            data,
        )

    def api_login(self, username, password):
        client = APIClient(enforce_csrf_checks=True)
        client.get(reverse("auth-csrf"))
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("auth-login"),
            {"username": username, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        return client, response

    def create_import_for(self, user):
        competencia = Competencia.objects.create(ano=2099, mes=1)
        ups = Ups.objects.create(
            codigo_gmus="9999902",
            id_unidade_gmus="rf02",
            nome="UPS FICTICIA RF02",
        )
        return Importacao.objects.create(
            nome_arquivo="rf02_inventario_ficticio.csv",
            hash_arquivo="a" * 64,
            tipo_relatorio="inventario",
            data_importacao=timezone.now(),
            status=Importacao.Status.CONCLUIDA,
            usuario=user,
            competencia=competencia,
            ups=ups,
        )

    def test_superuser_can_access_django_admin_user_area(self):
        self.login_admin()

        response = self.client.get(reverse("admin:auth_user_changelist"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_staff_cannot_administer_users_or_groups(self):
        self.client.force_login(self.staff)

        for url in (
            reverse("admin:auth_user_changelist"),
            reverse("admin:auth_user_add"),
            reverse("admin:auth_user_change", args=[self.staff.pk]),
            reverse("admin:auth_group_changelist"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertFalse(self.staff.has_perm("auth.view_user"))
        self.assertFalse(self.staff.has_perm("auth.add_user"))
        self.assertFalse(self.staff.has_perm("auth.change_user"))
        self.assertFalse(self.staff.has_perm("auth.delete_user"))
        self.assertFalse(self.staff.has_perm("auth.view_group"))
        self.assertFalse(self.staff.has_perm("auth.add_group"))
        self.assertFalse(self.staff.has_perm("auth.change_group"))
        self.assertFalse(self.staff.has_perm("auth.delete_group"))

    def test_superuser_creates_staff_and_new_staff_authenticates_in_stockflow(self):
        self.login_admin()
        new_password = "senha-novo-staff-segura"

        add_response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "novo_staff_rf02",
                "password1": new_password,
                "password2": new_password,
                "_save": "Salvar",
            },
        )
        self.assertEqual(add_response.status_code, status.HTTP_302_FOUND)

        user = get_user_model().objects.get(username="novo_staff_rf02")
        change_response = self.update_user_via_admin(user, is_staff=True)
        self.assertEqual(change_response.status_code, status.HTTP_302_FOUND)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

        _, login_response = self.api_login(user.username, new_password)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_deactivating_user_prevents_new_login(self):
        self.login_admin()

        response = self.update_user_via_admin(self.staff, is_active=False)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        _, login_response = self.api_login(self.staff.username, self.password)
        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_password_change_keeps_hash_and_new_password_works(self):
        self.login_admin()
        new_password = "senha-alterada-segura"

        response = self.client.post(
            reverse("admin:auth_user_password_change", args=[self.staff.pk]),
            {"password1": new_password, "password2": new_password},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.staff.refresh_from_db()
        self.assertNotEqual(self.staff.password, new_password)
        self.assertTrue(self.staff.check_password(new_password))
        _, login_response = self.api_login(self.staff.username, new_password)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_user_without_references_can_be_deleted(self):
        disposable_user = get_user_model().objects.create_user(
            username="usuario_descartavel_rf02",
            password=self.password,
            is_staff=True,
        )
        self.login_admin()

        response = self.client.post(
            reverse("admin:auth_user_delete", args=[disposable_user.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertFalse(
            get_user_model().objects.filter(pk=disposable_user.pk).exists()
        )

    def test_user_linked_to_import_cannot_be_deleted(self):
        importacao = self.create_import_for(self.staff)
        self.login_admin()

        response = self.client.post(
            reverse("admin:auth_user_delete", args=[self.staff.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Importacao.objects.filter(pk=importacao.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.staff.pk).exists())
        with self.assertRaises(ProtectedError):
            self.staff.delete()

    def test_user_with_import_history_can_be_deactivated(self):
        importacao = self.create_import_for(self.staff)
        self.login_admin()

        response = self.update_user_via_admin(self.staff, is_active=False)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.staff.refresh_from_db()
        importacao.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertEqual(importacao.usuario_id, self.staff.pk)
