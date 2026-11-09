from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from importacoes.models import Importacao, MovimentacaoEstoque
from importacoes.report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK
from medicamentos.models import Medicamento

from .models import CorrecaoValidacaoEstoque, SaldoEstoque


class MovementValidationApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff-validacao-fontes",
            is_staff=True,
        )
        self.julho = Competencia.objects.create(ano=2026, mes=7)
        self.agosto = Competencia.objects.create(ano=2026, mes=8)
        self.ups = Ups.objects.create(
            codigo_gmus="1234567",
            id_unidade_gmus="9",
            nome="FARMACIA TESTE",
        )
        self.medicamento = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE",
            unidade="COMPR",
        )
        self.url = reverse("estoque-validacao-movimentacoes")

    def importacao(self, competencia, tipo, status_importacao=Importacao.Status.CONCLUIDA):
        return Importacao.objects.create(
            nome_arquivo=f"{tipo}-{competencia}.csv",
            tipo_relatorio=tipo,
            data_importacao=timezone.now(),
            status=status_importacao,
            usuario=self.staff,
            competencia=competencia,
            ups=self.ups,
        )

    def criar_cenario(self, estoque_final):
        anterior = self.importacao(self.julho, REPORT_TYPE_STOCK)
        atual = self.importacao(self.agosto, REPORT_TYPE_STOCK)
        movimentos = self.importacao(self.agosto, REPORT_TYPE_MOVEMENT)
        SaldoEstoque.objects.create(
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.julho,
            importacao=anterior,
            quantidade=Decimal("100"),
        )
        SaldoEstoque.objects.create(
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.agosto,
            importacao=atual,
            quantidade=Decimal(estoque_final),
        )
        MovimentacaoEstoque.objects.create(
            importacao=movimentos,
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.agosto,
            data_inicial=date(2026, 8, 1),
            data_final=date(2026, 8, 31),
            saida=Decimal("10"),
        )
        return anterior, atual, movimentos

    def test_uses_only_concluded_sources(self):
        anterior = self.importacao(self.julho, REPORT_TYPE_STOCK)
        atual = self.importacao(self.agosto, REPORT_TYPE_STOCK)
        movimentos = self.importacao(self.agosto, REPORT_TYPE_MOVEMENT)
        SaldoEstoque.objects.create(
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.julho,
            importacao=anterior,
            quantidade=Decimal("100"),
        )
        SaldoEstoque.objects.create(
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.agosto,
            importacao=atual,
            quantidade=Decimal("90"),
        )
        MovimentacaoEstoque.objects.create(
            importacao=movimentos,
            medicamento=self.medicamento,
            ups=self.ups,
            competencia=self.agosto,
            data_inicial=date(2026, 8, 1),
            data_final=date(2026, 8, 31),
            saida=Decimal("10"),
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["totais"]["divergentes"], 0)
        self.assertEqual(response.data["fontes"]["estoque_anterior"]["importacao_id"], anterior.pk)
        self.assertEqual(response.data["fontes"]["movimentacoes"]["importacao_id"], movimentos.pk)
        self.assertEqual(response.data["fontes"]["estoque_final"]["importacao_id"], atual.pk)

    def test_rejects_partial_final_stock(self):
        self.importacao(self.julho, REPORT_TYPE_STOCK)
        self.importacao(
            self.agosto,
            REPORT_TYPE_STOCK,
            status_importacao=Importacao.Status.CONCLUIDA_PARCIAL,
        )
        self.importacao(self.agosto, REPORT_TYPE_MOVEMENT)
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("estoque final concluido", response.data["erro"])

    def test_blocks_validation_when_immediate_previous_competence_is_missing(self):
        junho = Competencia.objects.create(ano=2026, mes=6)
        self.importacao(junho, REPORT_TYPE_STOCK)
        self.importacao(self.agosto, REPORT_TYPE_STOCK)
        self.importacao(self.agosto, REPORT_TYPE_MOVEMENT)
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("estoque anterior", response.data["erro"])

    def test_rejects_non_numeric_source_ids(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            self.url,
            {"competencia": "abc", "ups": "xyz"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("IDs numericos", response.data["erro"])

    def test_manual_correction_only_validates_when_balance_closes(self):
        self.criar_cenario("95")
        self.client.force_authenticate(self.staff)

        invalid = self.client.post(
            self.url,
            {
                "competencia": self.agosto.pk,
                "ups": self.ups.pk,
                "medicamento": self.medicamento.pk,
                "estoque_corrigido": "94",
                "justificativa": "Conferencia manual do saldo.",
            },
            format="json",
        )

        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(invalid.data["estoque_esperado"], Decimal("90"))
        self.assertFalse(CorrecaoValidacaoEstoque.objects.exists())

        corrected = self.client.post(
            self.url,
            {
                "competencia": self.agosto.pk,
                "ups": self.ups.pk,
                "medicamento": self.medicamento.pk,
                "estoque_corrigido": "90",
                "justificativa": "Conferencia manual do saldo.",
            },
            format="json",
        )
        result = self.client.get(
            self.url,
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )

        self.assertEqual(corrected.status_code, status.HTTP_201_CREATED)
        self.assertEqual(result.data["totais"]["divergentes"], 0)
        self.assertEqual(result.data["totais"]["correcoes_manuais"], 1)
        self.assertEqual(result.data["totais"]["estoque_observado"], Decimal("90"))
        self.assertEqual(
            result.data["totais"]["estoque_observado_original"], Decimal("95")
        )
        registro = result.data["registros"][0]
        self.assertEqual(registro["situacao"], "conferido")
        self.assertEqual(registro["estoque_observado_original"], Decimal("95"))
        self.assertEqual(registro["correcao_manual"]["corrigido_por"], self.staff.username)

        medicamentos = self.client.get(
            reverse("medicamento-list"),
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )
        self.assertEqual(medicamentos.status_code, status.HTTP_200_OK)
        self.assertEqual(medicamentos.data[0]["situacao_validacao"], "validado")

    def test_reimported_source_invalidates_old_manual_correction(self):
        _, atual, _ = self.criar_cenario("95")
        self.client.force_authenticate(self.staff)
        self.client.post(
            self.url,
            {
                "competencia": self.agosto.pk,
                "ups": self.ups.pk,
                "medicamento": self.medicamento.pk,
                "estoque_corrigido": "90",
                "justificativa": "Conferencia manual do saldo.",
            },
            format="json",
        )
        atual.hash_arquivo = "nova-versao"
        atual.data_importacao = timezone.now() + timedelta(seconds=1)
        atual.save(update_fields=["hash_arquivo", "data_importacao"])

        result = self.client.get(
            self.url,
            {"competencia": self.agosto.pk, "ups": self.ups.pk},
        )

        self.assertEqual(result.data["totais"]["divergentes"], 1)
        self.assertEqual(result.data["totais"]["correcoes_manuais"], 0)

    def test_does_not_allow_correction_for_already_valid_item(self):
        self.criar_cenario("90")
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            self.url,
            {
                "competencia": self.agosto.pk,
                "ups": self.ups.pk,
                "medicamento": self.medicamento.pk,
                "estoque_corrigido": "90",
                "justificativa": "Tentativa desnecessaria.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(CorrecaoValidacaoEstoque.objects.exists())
