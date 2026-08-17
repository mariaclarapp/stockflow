from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from importacoes.models import Importacao

from .models import Competencia, Ups
from .services import CompetenciaService


class UpsModelTests(TestCase):
    def test_consolidation_configuration_defaults_to_enabled(self):
        ups = Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus="9",
            nome="UPS TESTE",
        )

        self.assertTrue(ups.participa_competencia)
        self.assertTrue(ups.compoe_estoque_convencional)

    def test_shared_code_allows_distinct_gmus_unit_identifiers(self):
        Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus="9",
            nome="FARMACIA",
        )
        Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus="10",
            nome="CAF",
        )

        self.assertEqual(Ups.objects.filter(codigo_gmus="2780046").count(), 2)

    def test_code_and_gmus_unit_identifier_are_unique_together(self):
        Ups.objects.create(
            codigo_gmus="2780046",
            id_unidade_gmus="9",
            nome="FARMACIA",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Ups.objects.create(
                codigo_gmus="2780046",
                id_unidade_gmus="9",
                nome="OUTRO NOME",
            )

    def test_complete_competence_counts_ups_with_shared_code_separately(self):
        user = get_user_model().objects.create_user(username="competencia-ups")
        competencia = Competencia.objects.create(ano=2026, mes=8)
        unidades = [
            Ups.objects.create(
                codigo_gmus="2780046",
                id_unidade_gmus=id_unidade,
                nome=nome,
            )
            for id_unidade, nome in (("9", "FARMACIA"), ("10", "CAF"))
        ]
        for ups in unidades:
            Importacao.objects.create(
                nome_arquivo=f"inventario-{ups.id_unidade_gmus}.csv",
                hash_arquivo="",
                tipo_relatorio="inventario",
                data_importacao=timezone.now(),
                status=Importacao.Status.CONCLUIDA,
                usuario=user,
                competencia=competencia,
                ups=ups,
            )

        self.assertEqual(
            CompetenciaService.identificar_competencia_completa(),
            competencia,
        )
