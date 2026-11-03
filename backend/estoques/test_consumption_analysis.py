from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from importacoes.models import Importacao, MovimentacaoEstoque
from importacoes.report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK
from medicamentos.models import Classificacao, Medicamento


class ConsumptionAnalysisApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff-analise-consumo",
            is_staff=True,
        )
        self.usuario_comum = get_user_model().objects.create_user(
            username="comum-analise-consumo",
        )
        self.julho = Competencia.objects.create(ano=2026, mes=7)
        self.agosto = Competencia.objects.create(ano=2026, mes=8)
        self.ups_a = Ups.objects.create(
            codigo_gmus="UPS-A",
            id_unidade_gmus="A",
            nome="UPS A",
        )
        self.ups_b = Ups.objects.create(
            codigo_gmus="UPS-B",
            id_unidade_gmus="B",
            nome="UPS B",
            participa_competencia=False,
        )
        self.medicamento_a = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO A",
            unidade="COMPR",
        )
        self.medicamento_b = Medicamento.objects.create(
            codigo_gmus="100.2",
            descricao="MEDICAMENTO B",
            unidade="FRASC",
        )
        self.url = reverse("analise-consumo")

    def criar_movimento(
        self,
        competencia,
        ups,
        medicamento,
        *,
        saida="0",
        compra="0",
        transferencia_saida="0",
    ):
        importacao, _ = Importacao.objects.get_or_create(
            competencia=competencia,
            ups=ups,
            tipo_relatorio=REPORT_TYPE_MOVEMENT,
            defaults={
                "nome_arquivo": f"mov-{competencia}-{ups.pk}.csv",
                "hash_arquivo": "",
                "data_importacao": timezone.now(),
                "status": Importacao.Status.CONCLUIDA,
                "usuario": self.staff,
            },
        )
        return MovimentacaoEstoque.objects.create(
            importacao=importacao,
            medicamento=medicamento,
            ups=ups,
            competencia=competencia,
            data_inicial=date(competencia.ano, competencia.mes, 1),
            data_final=date(competencia.ano, competencia.mes, 28),
            saida=Decimal(saida),
            compra=Decimal(compra),
            transferencia_saida=Decimal(transferencia_saida),
        )

    def parametros(self, **extras):
        return {
            "competencia_inicial": self.julho.pk,
            "competencia_final": self.agosto.pk,
            **extras,
        }

    def test_exige_usuario_staff(self):
        self.assertIn(
            self.client.get(self.url, self.parametros()).status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.client.force_authenticate(self.usuario_comum)
        self.assertEqual(
            self.client.get(self.url, self.parametros()).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_consumo_usa_somente_saida(self):
        self.criar_movimento(
            self.julho,
            self.ups_a,
            self.medicamento_a,
            saida="10",
            compra="100",
            transferencia_saida="40",
        )
        self.criar_movimento(
            self.agosto,
            self.ups_a,
            self.medicamento_a,
            saida="30",
            compra="20",
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(self.url, self.parametros())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resumo"]["consumo_total"], Decimal("40"))
        self.assertEqual(response.data["resumo"]["media_mensal"], Decimal("20"))
        self.assertEqual(
            response.data["resumo"]["saidas_operacionais_total"],
            Decimal("80"),
        )
        self.assertEqual(response.data["ranking"][0]["consumo"], Decimal("40"))
        self.assertEqual(
            response.data["ranking"][0]["media_mensal"], Decimal("20")
        )
        self.assertEqual(response.data["ranking"][0]["meses_com_consumo"], 2)
        self.assertEqual(
            [item["consumo"] for item in response.data["ranking"][0]["evolucao"]],
            [Decimal("10"), Decimal("30")],
        )
        self.assertEqual(
            response.data["ranking"][0]["pico_consumo"]["competencia"]["id"],
            self.agosto.pk,
        )

    def test_aplica_filtros_e_lista_medicamento_sem_consumo(self):
        classificacao = Classificacao.objects.create(nome="CONTROLADOS")
        self.medicamento_a.classificacoes.add(classificacao)
        self.criar_movimento(
            self.julho, self.ups_a, self.medicamento_a, saida="15"
        )
        self.criar_movimento(
            self.julho, self.ups_a, self.medicamento_b, saida="0"
        )
        self.criar_movimento(
            self.julho, self.ups_b, self.medicamento_a, saida="90"
        )
        self.client.force_authenticate(self.staff)

        filtrado = self.client.get(
            self.url,
            self.parametros(
                competencia_final=self.julho.pk,
                ups=self.ups_a.pk,
                busca="100.2",
            ),
        )
        por_classificacao = self.client.get(
            self.url,
            self.parametros(
                competencia_final=self.julho.pk,
                ups=self.ups_a.pk,
                classificacao=classificacao.pk,
            ),
        )

        self.assertEqual(filtrado.data["resumo"]["consumo_total"], Decimal("0"))
        self.assertEqual(filtrado.data["resumo"]["medicamentos_sem_consumo"], 1)
        self.assertEqual(
            filtrado.data["sem_consumo"][0]["id"], self.medicamento_b.pk
        )
        self.assertEqual(
            por_classificacao.data["resumo"]["consumo_total"], Decimal("15")
        )

    def test_inclui_ups_com_movimentacao_e_consumo_zero(self):
        self.criar_movimento(
            self.julho,
            self.ups_a,
            self.medicamento_a,
            saida="0",
            compra="100",
            transferencia_saida="40",
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            self.parametros(competencia_final=self.julho.pk),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["por_ups"]), 1)
        self.assertEqual(response.data["por_ups"][0]["id"], self.ups_a.pk)
        self.assertEqual(response.data["por_ups"][0]["consumo"], Decimal("0"))

    def test_filtra_analise_por_unidade(self):
        self.criar_movimento(
            self.julho, self.ups_a, self.medicamento_a, saida="12"
        )
        self.criar_movimento(
            self.julho, self.ups_a, self.medicamento_b, saida="40"
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            self.parametros(
                competencia_final=self.julho.pk,
                unidade="COMPR",
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resumo"]["consumo_total"], Decimal("12"))
        self.assertEqual(
            [item["id"] for item in response.data["ranking"]],
            [self.medicamento_a.pk],
        )

    def test_compara_dois_periodos(self):
        self.criar_movimento(
            self.julho, self.ups_a, self.medicamento_a, saida="20"
        )
        self.criar_movimento(
            self.agosto, self.ups_a, self.medicamento_a, saida="30"
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            self.parametros(
                competencia_inicial=self.agosto.pk,
                comparacao_inicial=self.julho.pk,
                comparacao_final=self.julho.pk,
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["comparacao"]["resumo"]["consumo_total"],
            Decimal("20"),
        )
        self.assertEqual(
            response.data["comparacao"]["variacao_percentual"],
            Decimal("50"),
        )

    def test_ignora_competencia_sem_qualquer_importacao(self):
        self.criar_movimento(
            self.agosto, self.ups_a, self.medicamento_a, saida="30"
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            self.parametros(competencia_inicial=self.agosto.pk),
        )

        self.assertEqual(response.data["qualidade"]["competencias_no_periodo"], 1)
        self.assertEqual(response.data["qualidade"]["competencias_com_dados"], 1)
        self.assertEqual(response.data["resumo"]["media_mensal"], Decimal("30"))
        self.assertEqual(response.data["qualidade"]["competencias_sem_dados"], [])

    def test_informa_competencia_com_estoque_mas_sem_movimentacao(self):
        Importacao.objects.create(
            competencia=self.julho,
            ups=self.ups_a,
            tipo_relatorio=REPORT_TYPE_STOCK,
            nome_arquivo="estoque-julho.csv",
            hash_arquivo="",
            data_importacao=timezone.now(),
            status=Importacao.Status.CONCLUIDA,
            usuario=self.staff,
        )
        self.criar_movimento(
            self.agosto, self.ups_a, self.medicamento_a, saida="30"
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(self.url, self.parametros())

        self.assertEqual(response.data["qualidade"]["competencias_no_periodo"], 2)
        self.assertEqual(response.data["qualidade"]["competencias_com_dados"], 1)
        self.assertEqual(
            response.data["qualidade"]["competencias_sem_dados"][0]["id"],
            self.julho.pk,
        )

    def test_ignora_importacao_parcial_na_media(self):
        movimento = self.criar_movimento(
            self.agosto, self.ups_a, self.medicamento_a, saida="30"
        )
        movimento.importacao.status = Importacao.Status.CONCLUIDA_PARCIAL
        movimento.importacao.save(update_fields=["status"])
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            self.parametros(competencia_inicial=self.agosto.pk),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resumo"]["consumo_total"], Decimal("0"))
        self.assertEqual(response.data["qualidade"]["competencias_com_dados"], 0)
