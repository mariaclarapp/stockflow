from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Classificacao, Medicamento, SubgrupoGmus
from .services import DesclassificacaoMedicamentosLoteService


class BulkMedicationDeclassificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username="staff_desclassificacao_lote",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.non_staff = get_user_model().objects.create_user(
            username="usuario_desclassificacao_lote",
            password="senha-ficticia",
        )
        cls.categoria = Classificacao.objects.create(nome="CATEGORIA PARA REMOVER")
        cls.outra_categoria = Classificacao.objects.create(nome="OUTRA CATEGORIA")
        cls.inativa = Classificacao.objects.create(nome="CATEGORIA INATIVA", ativo=False)
        cls.manipulado = Classificacao.objects.create(nome="MANIPULADO")
        cls.subgrupo = SubgrupoGmus.objects.create(
            codigo_gmus=95,
            nome="SUBGRUPO PARA DESCLASSIFICACAO",
        )
        cls.categorizado_a = Medicamento.objects.create(
            codigo_gmus="LOTE-DESCLASS-1",
            descricao="CATEGORIZADO A",
        )
        cls.categorizado_b = Medicamento.objects.create(
            codigo_gmus="LOTE-DESCLASS-2",
            descricao="CATEGORIZADO B",
        )
        cls.sem_categoria = Medicamento.objects.create(
            codigo_gmus="LOTE-DESCLASS-3",
            descricao="SEM CATEGORIA",
        )
        cls.com_subgrupo = Medicamento.objects.create(
            codigo_gmus="LOTE-DESCLASS-4",
            descricao="COM SUBGRUPO",
            subgrupo_gmus=cls.subgrupo,
        )
        cls.apenas_manipulado = Medicamento.objects.create(
            codigo_gmus="LOTE-DESCLASS-5",
            descricao="APENAS MANIPULADO",
        )
        cls.categorizado_a.classificacoes.add(
            cls.categoria,
            cls.outra_categoria,
            cls.manipulado,
        )
        cls.categorizado_b.classificacoes.add(cls.categoria)
        cls.com_subgrupo.classificacoes.add(cls.categoria)
        cls.apenas_manipulado.classificacoes.add(cls.manipulado)
        cls.url = reverse("medicamento-desclassificar-lote")

    def setUp(self):
        self.client.force_authenticate(self.staff)

    def remover(self, ids, classificacao=None):
        return self.client.post(
            self.url,
            {
                "medicamento_ids": ids,
                "classificacao_id": (classificacao or self.categoria).pk,
            },
            format="json",
        )

    def test_removes_category_from_one_medication(self):
        response = self.remover([self.categorizado_a.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["desclassificados"], 1)
        self.assertFalse(
            self.categorizado_a.classificacoes.filter(pk=self.categoria.pk).exists()
        )

    def test_removes_category_from_multiple_medications(self):
        response = self.remover(
            [self.categorizado_a.pk, self.categorizado_b.pk]
        )

        self.assertEqual(response.data["desclassificados"], 2)
        self.assertFalse(
            self.categoria.medicamentos.filter(
                pk__in=[self.categorizado_a.pk, self.categorizado_b.pk]
            ).exists()
        )

    def test_mixed_selection_reports_every_ignored_group(self):
        response = self.remover(
            [
                self.categorizado_a.pk,
                self.sem_categoria.pk,
                self.com_subgrupo.pk,
                999999,
            ]
        )

        self.assertEqual(response.data, {
            "selecionados": 4,
            "desclassificados": 1,
            "ignorados_subgrupo": 1,
            "ignorados_sem_classificacao": 1,
            "ignorados_inexistentes": 1,
        })
        self.assertTrue(
            self.com_subgrupo.classificacoes.filter(pk=self.categoria.pk).exists()
        )

    def test_preserves_other_common_category_and_manipulated_tag(self):
        response = self.remover([self.categorizado_a.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            self.categorizado_a.classificacoes.filter(
                pk=self.outra_categoria.pk
            ).exists()
        )
        self.assertTrue(
            self.categorizado_a.classificacoes.filter(pk=self.manipulado.pk).exists()
        )

    def test_ignores_medication_without_selected_category(self):
        response = self.remover([self.sem_categoria.pk, self.apenas_manipulado.pk])

        self.assertEqual(response.data["desclassificados"], 0)
        self.assertEqual(response.data["ignorados_sem_classificacao"], 2)
        self.assertTrue(
            self.apenas_manipulado.classificacoes.filter(pk=self.manipulado.pk).exists()
        )

    def test_rejects_manipulated_classification(self):
        response = self.remover([self.apenas_manipulado.pk], self.manipulado)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.apenas_manipulado.classificacoes.filter(pk=self.manipulado.pk).exists()
        )

    def test_allows_removing_an_inactive_existing_classification(self):
        self.categorizado_b.classificacoes.add(self.inativa)

        response = self.remover([self.categorizado_b.pk], self.inativa)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["desclassificados"], 1)
        self.assertFalse(
            self.categorizado_b.classificacoes.filter(pk=self.inativa.pk).exists()
        )

    def test_rejects_nonexistent_classification(self):
        response = self.client.post(
            self.url,
            {
                "medicamento_ids": [self.categorizado_a.pk],
                "classificacao_id": 999999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            self.categorizado_a.classificacoes.filter(pk=self.categoria.pk).exists()
        )

    def test_removes_duplicate_ids_and_reports_nonexistent_ids(self):
        response = self.remover(
            [self.categorizado_a.pk, self.categorizado_a.pk, 999999]
        )

        self.assertEqual(response.data["selecionados"], 2)
        self.assertEqual(response.data["desclassificados"], 1)
        self.assertEqual(response.data["ignorados_inexistentes"], 1)

    def test_rejects_more_than_fifty_ids(self):
        response = self.remover(list(range(1, 52)))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("medicamento_ids", response.data)

    def test_requires_staff_authorization(self):
        self.client.force_authenticate(self.non_staff)
        non_staff_response = self.remover([self.categorizado_a.pk])
        self.client.force_authenticate(user=None)
        anonymous_response = self.remover([self.categorizado_a.pk])

        self.assertEqual(non_staff_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            anonymous_response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_declassified_medication_returns_to_uncategorized_filter(self):
        self.categorizado_b.classificacoes.add(self.manipulado)
        self.remover([self.categorizado_b.pk])

        response = self.client.get(
            reverse("medicamento-list"),
            {"sem_categoria": "true", "search": self.categorizado_b.codigo_gmus},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [self.categorizado_b.pk])
        self.assertEqual(
            [item["nome"] for item in response.data[0]["classificacoes"]],
            ["MANIPULADO"],
        )

    def test_medication_can_be_classified_again_after_declassification(self):
        medicamento = self.sem_categoria
        medicamento.classificacoes.add(self.manipulado)
        classificar_url = reverse("medicamento-classificar-lote")
        payload = {
            "medicamento_ids": [medicamento.pk],
            "classificacao_id": self.categoria.pk,
        }

        primeira_classificacao = self.client.post(
            classificar_url,
            payload,
            format="json",
        )
        medicamento.refresh_from_db()
        self.assertEqual(primeira_classificacao.data["classificados"], 1)
        self.assertTrue(
            medicamento.classificacoes.filter(pk=self.categoria.pk).exists()
        )

        desclassificacao = self.remover([medicamento.pk])
        medicamento.refresh_from_db()
        self.assertEqual(desclassificacao.data["desclassificados"], 1)
        self.assertFalse(
            medicamento.classificacoes.filter(pk=self.categoria.pk).exists()
        )
        self.assertTrue(
            medicamento.classificacoes.filter(pk=self.manipulado.pk).exists()
        )

        sem_categoria = self.client.get(
            reverse("medicamento-list"),
            {"sem_categoria": "true", "search": medicamento.codigo_gmus},
        )
        segunda_classificacao = self.client.post(
            classificar_url,
            payload,
            format="json",
        )
        medicamento.refresh_from_db()

        self.assertEqual(
            [item["id"] for item in sem_categoria.data],
            [medicamento.pk],
        )
        self.assertEqual(segunda_classificacao.data["classificados"], 1)
        self.assertTrue(
            medicamento.classificacoes.filter(pk=self.categoria.pk).exists()
        )
        self.assertEqual(
            medicamento.classificacoes.filter(pk=self.manipulado.pk).count(),
            1,
        )

    def test_public_availability_keeps_manipulated_rule(self):
        self.remover([self.categorizado_a.pk])

        response = self.client.get(
            reverse("public-medicamento-list"),
            {"search": self.categorizado_a.codigo_gmus},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data[0]["disponibilidade"],
            "Disponível sob manipulação, confirmar disponibilidade",
        )
        self.assertEqual(
            set(response.data[0]),
            {"codigo_gmus", "descricao", "unidade", "disponibilidade"},
        )

    def test_unexpected_failure_rolls_back_every_removal(self):
        associacao = Medicamento.classificacoes.through

        def delete_one_then_fail(medicamento_ids, classificacao_id):
            associacao.objects.filter(
                medicamento_id=medicamento_ids[0],
                classificacao_id=classificacao_id,
            ).delete()
            raise RuntimeError("falha ficticia")

        with patch.object(
            DesclassificacaoMedicamentosLoteService,
            "_remover_associacoes",
            side_effect=delete_one_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                self.remover([self.categorizado_a.pk, self.categorizado_b.pk])

        self.assertEqual(
            associacao.objects.filter(
                medicamento_id__in=[self.categorizado_a.pk, self.categorizado_b.pk],
                classificacao_id=self.categoria.pk,
            ).count(),
            2,
        )
