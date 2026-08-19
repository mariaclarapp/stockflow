from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Classificacao, Medicamento, SubgrupoGmus
from .services import ClassificacaoMedicamentosLoteService


class BulkMedicationClassificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username="staff_classificacao_lote",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.non_staff = get_user_model().objects.create_user(
            username="usuario_classificacao_lote",
            password="senha-ficticia",
        )
        cls.categoria = Classificacao.objects.create(nome="CATEGORIA EM LOTE")
        cls.categoria_existente = Classificacao.objects.create(
            nome="CATEGORIA EXISTENTE"
        )
        cls.manipulado = Classificacao.objects.create(nome="MANIPULADO")
        cls.inativa = Classificacao.objects.create(nome="INATIVA", ativo=False)
        cls.subgrupo = SubgrupoGmus.objects.create(
            codigo_gmus=94,
            nome="SUBGRUPO OFICIAL",
        )
        cls.elegivel_a = Medicamento.objects.create(
            codigo_gmus="LOTE-CLASS-1",
            descricao="ELEGIVEL A",
        )
        cls.elegivel_b = Medicamento.objects.create(
            codigo_gmus="LOTE-CLASS-2",
            descricao="ELEGIVEL B",
        )
        cls.com_subgrupo = Medicamento.objects.create(
            codigo_gmus="LOTE-CLASS-3",
            descricao="COM SUBGRUPO",
            subgrupo_gmus=cls.subgrupo,
        )
        cls.ja_classificado = Medicamento.objects.create(
            codigo_gmus="LOTE-CLASS-4",
            descricao="JA CLASSIFICADO",
        )
        cls.ja_classificado.classificacoes.add(cls.categoria_existente)
        cls.apenas_manipulado = Medicamento.objects.create(
            codigo_gmus="LOTE-CLASS-5",
            descricao="APENAS MANIPULADO",
        )
        cls.apenas_manipulado.classificacoes.add(cls.manipulado)
        cls.url = reverse("medicamento-classificar-lote")

    def setUp(self):
        self.client.force_authenticate(self.staff)

    def aplicar(self, ids, classificacao=None):
        return self.client.post(
            self.url,
            {
                "medicamento_ids": ids,
                "classificacao_id": (classificacao or self.categoria).pk,
            },
            format="json",
        )

    def test_classifies_multiple_eligible_medications(self):
        response = self.aplicar([self.elegivel_a.pk, self.elegivel_b.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selecionados"], 2)
        self.assertEqual(response.data["classificados"], 2)
        self.assertTrue(self.elegivel_a.classificacoes.filter(pk=self.categoria.pk).exists())
        self.assertTrue(self.elegivel_b.classificacoes.filter(pk=self.categoria.pk).exists())

    def test_ignores_medication_with_gmus_subgroup(self):
        response = self.aplicar([self.elegivel_a.pk, self.com_subgrupo.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["classificados"], 1)
        self.assertEqual(response.data["ignorados_subgrupo"], 1)
        self.assertFalse(
            self.com_subgrupo.classificacoes.filter(pk=self.categoria.pk).exists()
        )

    def test_does_not_replace_existing_manual_category(self):
        response = self.aplicar([self.ja_classificado.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["classificados"], 0)
        self.assertEqual(response.data["ignorados_ja_classificados"], 1)
        self.assertEqual(
            list(self.ja_classificado.classificacoes.values_list("pk", flat=True)),
            [self.categoria_existente.pk],
        )

    def test_mixed_selection_applies_only_to_eligible_medications(self):
        response = self.aplicar(
            [
                self.elegivel_a.pk,
                self.apenas_manipulado.pk,
                self.com_subgrupo.pk,
                self.ja_classificado.pk,
            ]
        )

        self.assertEqual(response.data["selecionados"], 4)
        self.assertEqual(response.data["classificados"], 2)
        self.assertEqual(response.data["ignorados_subgrupo"], 1)
        self.assertEqual(response.data["ignorados_ja_classificados"], 1)
        self.assertTrue(
            self.apenas_manipulado.classificacoes.filter(pk=self.categoria.pk).exists()
        )
        self.assertTrue(
            self.apenas_manipulado.classificacoes.filter(pk=self.manipulado.pk).exists()
        )

    def test_rejects_manipulated_and_inactive_classifications(self):
        manipulated_response = self.aplicar(
            [self.elegivel_a.pk],
            self.manipulado,
        )
        inactive_response = self.aplicar([self.elegivel_a.pk], self.inativa)

        self.assertEqual(
            manipulated_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(inactive_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.elegivel_a.classificacoes.exists())

    def test_rejects_nonexistent_classification(self):
        response = self.client.post(
            self.url,
            {
                "medicamento_ids": [self.elegivel_a.pk],
                "classificacao_id": 999999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(self.elegivel_a.classificacoes.exists())

    def test_removes_repeated_ids_and_reports_nonexistent_ids(self):
        response = self.aplicar(
            [self.elegivel_a.pk, self.elegivel_a.pk, 999999]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selecionados"], 2)
        self.assertEqual(response.data["classificados"], 1)
        self.assertEqual(response.data["ignorados_inexistentes"], 1)

    def test_rejects_more_than_fifty_ids(self):
        response = self.aplicar(list(range(1, 52)))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("medicamento_ids", response.data)

    def test_operation_is_idempotent(self):
        first = self.aplicar([self.elegivel_a.pk])
        second = self.aplicar([self.elegivel_a.pk])

        self.assertEqual(first.data["classificados"], 1)
        self.assertEqual(second.data["classificados"], 0)
        self.assertEqual(second.data["ignorados_ja_classificados"], 1)
        self.assertEqual(
            self.elegivel_a.classificacoes.filter(pk=self.categoria.pk).count(),
            1,
        )

    def test_requires_staff_authorization(self):
        self.client.force_authenticate(self.non_staff)
        non_staff_response = self.aplicar([self.elegivel_a.pk])
        self.client.force_authenticate(user=None)
        anonymous_response = self.aplicar([self.elegivel_a.pk])

        self.assertEqual(non_staff_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            anonymous_response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unexpected_failure_rolls_back_every_association(self):
        associacao = Medicamento.classificacoes.through

        def create_one_then_fail(medicamento_ids, classificacao_id):
            associacao.objects.create(
                medicamento_id=medicamento_ids[0],
                classificacao_id=classificacao_id,
            )
            raise RuntimeError("falha ficticia")

        with patch.object(
            ClassificacaoMedicamentosLoteService,
            "_criar_associacoes",
            side_effect=create_one_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                self.aplicar([self.elegivel_a.pk, self.elegivel_b.pk])

        self.assertFalse(
            associacao.objects.filter(classificacao_id=self.categoria.pk).exists()
        )
