from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Classificacao, Medicamento


class ClassificationManagementApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff_classificacoes",
            password="senha-ficticia",
            is_staff=True,
        )
        self.non_staff = get_user_model().objects.create_user(
            username="usuario_classificacoes",
            password="senha-ficticia",
        )
        self.classification = Classificacao.objects.create(
            nome="ESSENCIAL",
            cor="#0B8178",
            descricao="Classificacao administrativa.",
        )
        self.manipulated = Classificacao.objects.create(
            nome="MANIPULADO",
            cor="#B7791F",
            ativo=True,
        )
        self.list_url = reverse("classificacao-list")

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.staff)

    def test_staff_can_list_and_create_classification(self):
        self.authenticate()

        list_response = self.client.get(self.list_url)
        create_response = self.client.post(
            self.list_url,
            {
                "nome": "CONTROLADO",
                "cor": "#336699",
                "descricao": "Uso administrativo.",
                "ativo": True,
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Classificacao.objects.filter(nome="CONTROLADO").exists())

    def test_anonymous_and_non_staff_cannot_manage_classifications(self):
        anonymous = self.client.get(self.list_url)
        self.authenticate(self.non_staff)
        non_staff_list = self.client.get(self.list_url)
        non_staff_create = self.client.post(
            self.list_url,
            {"nome": "BLOQUEADA"},
            format="json",
        )

        self.assertIn(
            anonymous.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertEqual(non_staff_list.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(non_staff_create.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Classificacao.objects.filter(nome="BLOQUEADA").exists())

    def test_duplicate_name_is_rejected_case_insensitively(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {"nome": "essencial", "ativo": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Classificacao.objects.filter(nome__iexact="essencial").count(), 1)

    def test_staff_can_patch_and_deactivate_regular_classification(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.classification.pk])

        response = self.client.patch(
            url,
            {
                "cor": "#123ABC",
                "descricao": "Descricao atualizada.",
                "ativo": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.classification.refresh_from_db()
        self.assertEqual(self.classification.cor, "#123ABC")
        self.assertEqual(self.classification.descricao, "Descricao atualizada.")
        self.assertFalse(self.classification.ativo)

    def test_invalid_color_is_rejected(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.classification.pk])

        response = self.client.patch(url, {"cor": "verde"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cor", response.data)

    def test_put_is_not_allowed(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.classification.pk])

        put_response = self.client.put(url, {"nome": "OUTRA"}, format="json")

        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Classificacao.objects.filter(pk=self.classification.pk).exists())

    def test_staff_can_delete_regular_classification_without_associations(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.classification.pk])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Classificacao.objects.filter(pk=self.classification.pk).exists())

    def test_delete_is_blocked_when_classification_has_associations(self):
        medicamento = Medicamento.objects.create(
            codigo_gmus="TESTE-DELETE-CLASS",
            descricao="MEDICAMENTO ASSOCIADO",
        )
        medicamento.classificacoes.add(self.classification)
        self.authenticate()

        response = self.client.delete(
            reverse("classificacao-detail", args=[self.classification.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Remova as associacoes", response.data["erro"])
        self.assertTrue(Classificacao.objects.filter(pk=self.classification.pk).exists())
        self.assertTrue(medicamento.classificacoes.filter(pk=self.classification.pk).exists())

    def test_manipulated_classification_cannot_be_deleted(self):
        self.authenticate()

        response = self.client.delete(
            reverse("classificacao-detail", args=[self.manipulated.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Classificacao.objects.filter(pk=self.manipulated.pk).exists())

    def test_anonymous_and_non_staff_cannot_delete_classification(self):
        url = reverse("classificacao-detail", args=[self.classification.pk])

        anonymous = self.client.delete(url)
        self.authenticate(self.non_staff)
        non_staff = self.client.delete(url)

        self.assertIn(
            anonymous.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertEqual(non_staff.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Classificacao.objects.filter(pk=self.classification.pk).exists())

    def test_manipulated_name_and_active_state_are_protected(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.manipulated.pk])

        rename = self.client.patch(url, {"nome": "OUTRO NOME"}, format="json")
        deactivate = self.client.patch(url, {"ativo": False}, format="json")

        self.assertEqual(rename.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deactivate.status_code, status.HTTP_400_BAD_REQUEST)
        self.manipulated.refresh_from_db()
        self.assertEqual(self.manipulated.nome, "MANIPULADO")
        self.assertTrue(self.manipulated.ativo)

    def test_manipulated_color_and_description_can_be_edited(self):
        self.authenticate()
        url = reverse("classificacao-detail", args=[self.manipulated.pk])

        response = self.client.patch(
            url,
            {"cor": "#AA7700", "descricao": "Preparacao sob manipulacao."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.manipulated.refresh_from_db()
        self.assertEqual(self.manipulated.cor, "#AA7700")
        self.assertEqual(self.manipulated.descricao, "Preparacao sob manipulacao.")

    def test_second_manipulated_classification_is_not_created(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {"nome": "manipulado", "ativo": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Classificacao.objects.filter(nome__iexact="MANIPULADO").count(), 1)


class MedicationClassificationAssociationApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff_associacoes",
            password="senha-ficticia",
            is_staff=True,
        )
        self.non_staff = get_user_model().objects.create_user(
            username="usuario_associacoes",
            password="senha-ficticia",
        )
        self.medicine = Medicamento.objects.create(
            codigo_gmus="TESTE-CLASS-1",
            descricao="MEDICAMENTO ADMINISTRATIVO / 10MG",
            unidade="COMPR",
        )
        self.manipulated_medicine = Medicamento.objects.create(
            codigo_gmus="TESTE-CLASS-2",
            descricao="MEDICAMENTO (MANIPULADO) / 20MG",
            unidade="CAPS",
        )
        self.active = Classificacao.objects.create(nome="PRIORITARIO", ativo=True)
        self.inactive = Classificacao.objects.create(nome="INATIVA", ativo=False)
        self.manipulated = Classificacao.objects.create(nome="MANIPULADO", ativo=True)

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.staff)

    def association_url(self, medicine=None):
        return reverse(
            "medicamento-associar-classificacao",
            args=[(medicine or self.medicine).pk],
        )

    def removal_url(self, classification, medicine=None):
        return reverse(
            "medicamento-desassociar-classificacao",
            args=[(medicine or self.medicine).pk, classification.pk],
        )

    def test_active_classification_can_be_associated_idempotently(self):
        self.authenticate()
        payload = {"classificacao_id": self.active.pk}

        first = self.client.post(self.association_url(), payload, format="json")
        second = self.client.post(self.association_url(), payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(self.medicine.classificacoes.filter(pk=self.active.pk).count(), 1)
        self.assertEqual(second.data["classificacoes"][0]["nome"], "PRIORITARIO")

    def test_inactive_classification_cannot_be_associated(self):
        self.authenticate()

        response = self.client.post(
            self.association_url(),
            {"classificacao_id": self.inactive.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.medicine.classificacoes.filter(pk=self.inactive.pk).exists())

    def test_regular_classification_can_be_removed(self):
        self.authenticate()
        self.medicine.classificacoes.add(self.active)

        response = self.client.delete(self.removal_url(self.active))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.medicine.classificacoes.filter(pk=self.active.pk).exists())

    def test_manipulated_cannot_be_removed_while_description_has_marker(self):
        self.authenticate()
        self.manipulated_medicine.classificacoes.add(self.manipulated)

        response = self.client.delete(
            self.removal_url(self.manipulated, self.manipulated_medicine)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.manipulated_medicine.classificacoes.filter(
                pk=self.manipulated.pk
            ).exists()
        )

    def test_manipulated_can_be_removed_without_explicit_marker(self):
        self.authenticate()
        self.medicine.classificacoes.add(self.manipulated)

        response = self.client.delete(self.removal_url(self.manipulated))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.medicine.classificacoes.filter(pk=self.manipulated.pk).exists())

    def test_missing_medicine_and_classification_return_not_found(self):
        self.authenticate()
        missing_medicine = reverse(
            "medicamento-associar-classificacao",
            args=[999999],
        )
        missing_classification = reverse(
            "medicamento-desassociar-classificacao",
            args=[self.medicine.pk, 999999],
        )

        medicine_response = self.client.post(
            missing_medicine,
            {"classificacao_id": self.active.pk},
            format="json",
        )
        classification_response = self.client.delete(missing_classification)

        self.assertEqual(medicine_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(classification_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_and_non_staff_cannot_change_associations(self):
        anonymous = self.client.post(
            self.association_url(),
            {"classificacao_id": self.active.pk},
            format="json",
        )
        self.authenticate(self.non_staff)
        non_staff = self.client.post(
            self.association_url(),
            {"classificacao_id": self.active.pk},
            format="json",
        )

        self.assertIn(
            anonymous.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertEqual(non_staff.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(self.medicine.classificacoes.exists())

    def test_public_api_keeps_fields_private_and_uses_manipulated_rule(self):
        self.authenticate()
        association = self.client.post(
            self.association_url(self.manipulated_medicine),
            {"classificacao_id": self.manipulated.pk},
            format="json",
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("public-medicamento-list"),
            {"search": self.manipulated_medicine.codigo_gmus},
        )

        self.assertEqual(association.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data[0]),
            {"codigo_gmus", "descricao", "unidade", "disponibilidade"},
        )
        self.assertEqual(
            response.data[0]["disponibilidade"],
            "Disponível sob manipulação, confirmar disponibilidade",
        )
