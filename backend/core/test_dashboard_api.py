from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from estoques.models import Estoque
from importacoes.models import Importacao
from medicamentos.models import Medicamento

from .models import Competencia, Ups


class DashboardResumoApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff-dashboard",
            is_staff=True,
        )
        self.non_staff = get_user_model().objects.create_user(
            username="comum-dashboard",
        )
        self.url = reverse("dashboard-resumo")

    def criar_ups(self, id_unidade, nome):
        return Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus=id_unidade,
            nome=nome,
        )

    def criar_importacao(self, competencia, ups, import_status):
        return Importacao.objects.create(
            nome_arquivo=f"inventario-{ups.id_unidade_gmus}.csv",
            hash_arquivo="a" * 64,
            tipo_relatorio="inventario",
            data_importacao=timezone.now(),
            status=import_status,
            usuario=self.staff,
            competencia=competencia,
            ups=ups,
        )

    def test_requires_staff_user(self):
        anonymous_response = self.client.get(self.url)
        self.client.force_authenticate(self.non_staff)
        non_staff_response = self.client.get(self.url)

        self.assertIn(
            anonymous_response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertEqual(
            non_staff_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_returns_empty_state_without_complete_competence(self):
        ups_a = self.criar_ups("9", "FARMACIA")
        self.criar_ups("10", "CAF")
        competencia = Competencia.objects.create(ano=2026, mes=8)
        self.criar_importacao(
            competencia,
            ups_a,
            Importacao.Status.CONCLUIDA,
        )
        Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE",
            unidade="COMPR",
        )
        self.client.force_authenticate(self.staff)

        with self.assertNumQueries(3):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["competencia_atual"])
        self.assertEqual(response.data["ups"], {"participantes": 2, "importadas": 0})
        self.assertEqual(response.data["importacoes"], [])
        self.assertEqual(response.data["totais"], {"medicamentos": 1, "estoques": 0})

    def test_returns_complete_competence_imports_and_real_totals(self):
        farmacia = self.criar_ups("9", "FARMACIA MUNICIPAL")
        caf = self.criar_ups("10", "CAF")
        competencia = Competencia.objects.create(ano=2026, mes=8)
        importacao_farmacia = self.criar_importacao(
            competencia,
            farmacia,
            Importacao.Status.CONCLUIDA,
        )
        importacao_caf = self.criar_importacao(
            competencia,
            caf,
            Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )
        medicamentos = [
            Medicamento.objects.create(
                codigo_gmus=f"100.{indice}",
                descricao=f"MEDICAMENTO {indice}",
                unidade="COMPR",
            )
            for indice in range(1, 4)
        ]
        for medicamento, importacao in (
            (medicamentos[0], importacao_farmacia),
            (medicamentos[1], importacao_farmacia),
            (medicamentos[1], importacao_caf),
        ):
            Estoque.objects.create(
                medicamento=medicamento,
                ups=importacao.ups,
                competencia=competencia,
                importacao=importacao,
                quantidade=Decimal("10.000"),
            )
        self.client.force_authenticate(self.staff)

        with self.assertNumQueries(5):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["competencia_atual"],
            {
                "id": competencia.pk,
                "ano": 2026,
                "mes": 8,
                "completa": True,
            },
        )
        self.assertEqual(response.data["ups"], {"participantes": 2, "importadas": 2})
        self.assertEqual(response.data["totais"], {"medicamentos": 3, "estoques": 3})
        self.assertEqual(len(response.data["importacoes"]), 2)
        imports_by_unit = {
            item["ups"]["id_unidade_gmus"]: item
            for item in response.data["importacoes"]
        }
        self.assertEqual(imports_by_unit["9"]["status"], "concluida")
        self.assertEqual(imports_by_unit["9"]["registros_estoque"], 2)
        self.assertEqual(
            imports_by_unit["10"]["status"],
            "concluida_com_alertas",
        )
        self.assertEqual(imports_by_unit["10"]["registros_estoque"], 1)
        self.assertEqual(imports_by_unit["10"]["ups"]["nome"], "CAF")
