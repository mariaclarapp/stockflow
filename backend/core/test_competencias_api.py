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


class CompetenciasAcompanhamentoApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff-competencias",
            is_staff=True,
        )
        self.non_staff = get_user_model().objects.create_user(
            username="comum-competencias",
        )
        self.url = reverse("competencias-acompanhamento")

    def criar_ups(self, id_unidade, nome, participa=True):
        return Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus=id_unidade,
            nome=nome,
            participa_competencia=participa,
        )

    def criar_importacao(self, competencia, ups, import_status):
        return Importacao.objects.create(
            nome_arquivo=f"inventario-{competencia}-{ups.id_unidade_gmus}.csv",
            hash_arquivo=(ups.id_unidade_gmus * 64)[:64],
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
        self.assertEqual(non_staff_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_empty_state_without_competences(self):
        self.criar_ups("9", "FARMACIA MUNICIPAL")
        self.client.force_authenticate(self.staff)

        with self.assertNumQueries(2):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["competencia_completa_mais_recente"])
        self.assertEqual(response.data["competencias"], [])

    def test_tracks_complete_incomplete_partial_and_missing_imports(self):
        farmacia = self.criar_ups("9", "FARMACIA MUNICIPAL")
        caf = self.criar_ups("10", "CAF")
        manipulacao = self.criar_ups("19", "FARMACIA DE MANIPULACAO")
        self.criar_ups("99", "UPS NAO PARTICIPANTE", participa=False)

        completa_anterior = Competencia.objects.create(ano=2026, mes=7)
        mais_recente_incompleta = Competencia.objects.create(ano=2026, mes=8)

        importacao_farmacia_julho = self.criar_importacao(
            completa_anterior,
            farmacia,
            Importacao.Status.CONCLUIDA,
        )
        self.criar_importacao(
            completa_anterior,
            caf,
            Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )
        self.criar_importacao(
            completa_anterior,
            manipulacao,
            Importacao.Status.CONCLUIDA,
        )
        self.criar_importacao(
            mais_recente_incompleta,
            farmacia,
            Importacao.Status.CONCLUIDA,
        )
        self.criar_importacao(
            mais_recente_incompleta,
            caf,
            Importacao.Status.CONCLUIDA_PARCIAL,
        )

        medicamento = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE",
            unidade="COMPR",
        )
        for _ in range(2):
            Estoque.objects.create(
                medicamento=medicamento,
                ups=farmacia,
                competencia=completa_anterior,
                importacao=importacao_farmacia_julho,
                quantidade=Decimal("5.000"),
            )

        self.client.force_authenticate(self.staff)

        with self.assertNumQueries(3):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["competencia_completa_mais_recente"],
            {
                "id": completa_anterior.pk,
                "ano": 2026,
                "mes": 7,
            },
        )
        self.assertEqual(
            [(item["ano"], item["mes"]) for item in response.data["competencias"]],
            [(2026, 8), (2026, 7)],
        )

        agosto = response.data["competencias"][0]
        self.assertFalse(agosto["completa"])
        self.assertEqual(agosto["ups"]["esperadas"], 3)
        self.assertEqual(agosto["ups"]["importadas_validas"], 1)
        agosto_por_unidade = {
            item["id_unidade_gmus"]: item for item in agosto["ups"]["situacoes"]
        }
        self.assertTrue(agosto_por_unidade["10"]["importada"])
        self.assertEqual(
            agosto_por_unidade["10"]["status"],
            Importacao.Status.CONCLUIDA_PARCIAL,
        )
        self.assertFalse(agosto_por_unidade["19"]["importada"])
        self.assertIsNone(agosto_por_unidade["19"]["status"])
        self.assertIsNone(agosto_por_unidade["19"]["data_importacao"])
        self.assertIsNone(agosto_por_unidade["19"]["registros_estoque"])
        self.assertNotIn("99", agosto_por_unidade)

        julho = response.data["competencias"][1]
        self.assertTrue(julho["completa"])
        self.assertEqual(julho["ups"]["importadas_validas"], 3)
        julho_por_unidade = {
            item["id_unidade_gmus"]: item for item in julho["ups"]["situacoes"]
        }
        self.assertEqual(julho_por_unidade["9"]["registros_estoque"], 2)
        self.assertEqual(
            julho_por_unidade["10"]["status"],
            Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )

