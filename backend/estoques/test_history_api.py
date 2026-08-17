from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from importacoes.models import Importacao
from medicamentos.models import Medicamento

from .models import Estoque, Lote


class HistoricoMedicamentoApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff_historico",
            password="senha-ficticia",
            is_staff=True,
        )
        self.usuario_comum = get_user_model().objects.create_user(
            username="comum_historico",
            password="senha-ficticia",
        )
        self.medicamento = Medicamento.objects.create(
            codigo_gmus="MED-HIST-1",
            descricao="MEDICAMENTO HISTORICO",
            unidade="COMPR",
        )
        self.ups_a = Ups.objects.create(
            codigo_gmus="UPS-HIST-A",
            id_unidade_gmus="A",
            nome="UNIDADE A",
        )
        self.ups_b = Ups.objects.create(
            codigo_gmus="UPS-HIST-B",
            id_unidade_gmus="B",
            nome="UNIDADE B",
        )
        self.ups_nao_convencional = Ups.objects.create(
            codigo_gmus="UPS-HIST-NC",
            id_unidade_gmus="NC",
            nome="UNIDADE NAO CONVENCIONAL",
            participa_competencia=False,
            compoe_estoque_convencional=False,
        )
        self.url = reverse(
            "medicamento-historico",
            kwargs={"pk": self.medicamento.pk},
        )

    def autenticar(self, usuario=None):
        self.client.force_authenticate(user=usuario or self.staff)

    def criar_competencia(self, ano, mes):
        return Competencia.objects.create(ano=ano, mes=mes)

    def criar_importacao(
        self,
        competencia,
        ups,
        status_importacao=Importacao.Status.CONCLUIDA,
    ):
        return Importacao.objects.create(
            nome_arquivo=f"inventario-{competencia.pk}-{ups.pk}.csv",
            hash_arquivo="",
            tipo_relatorio="inventario",
            data_importacao=timezone.now(),
            status=status_importacao,
            usuario=self.staff,
            competencia=competencia,
            ups=ups,
        )

    def completar_competencia(
        self,
        competencia,
        status_importacao=Importacao.Status.CONCLUIDA,
    ):
        for ups in (self.ups_a, self.ups_b):
            self.criar_importacao(competencia, ups, status_importacao)

    def criar_estoque(
        self,
        competencia,
        ups,
        quantidade,
        lote_codigo=None,
        medicamento=None,
    ):
        lote = None
        if lote_codigo is not None:
            lote = Lote.objects.create(
                medicamento=medicamento or self.medicamento,
                codigo_lote=lote_codigo,
                data_validade=date(2028, 12, 31),
            )
        importacao = Importacao.objects.get(
            competencia=competencia,
            ups=ups,
            tipo_relatorio="inventario",
        )
        return Estoque.objects.create(
            medicamento=medicamento or self.medicamento,
            ups=ups,
            competencia=competencia,
            lote=lote,
            importacao=importacao,
            quantidade=Decimal(quantidade),
        )

    def test_requer_staff_e_permite_usuario_administrativo(self):
        respostas_negadas = [
            self.client.get(self.url),
        ]
        self.autenticar(self.usuario_comum)
        respostas_negadas.append(self.client.get(self.url))

        for resposta in respostas_negadas:
            self.assertIn(
                resposta.status_code,
                [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            )

        self.autenticar()
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)

    def test_medicamento_inexistente_retorna_404(self):
        self.autenticar()
        url = reverse("medicamento-historico", kwargs={"pk": 999999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sem_competencia_completa_retorna_estoque_atual_nulo(self):
        self.autenticar()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["estoque_atual"])
        self.assertEqual(response.data["historico"], [])

    def test_medicamento_ausente_na_competencia_completa_retorna_zero(self):
        competencia = self.criar_competencia(2026, 8)
        self.completar_competencia(competencia)
        self.autenticar()

        response = self.client.get(self.url)

        atual = response.data["estoque_atual"]
        self.assertEqual(atual["competencia"]["id"], competencia.pk)
        self.assertTrue(atual["competencia"]["completa"])
        self.assertEqual(atual["quantidade_consolidada_convencional"], "0.000")
        self.assertEqual(atual["por_ups"], [])

    def test_competencia_incompleta_mais_recente_usa_fallback_e_aparece_no_historico(self):
        anterior = self.criar_competencia(2026, 7)
        recente = self.criar_competencia(2026, 8)
        self.completar_competencia(anterior)
        self.criar_importacao(recente, self.ups_a)
        self.criar_estoque(anterior, self.ups_a, "10.000")
        self.criar_estoque(recente, self.ups_a, "99.000")
        self.autenticar()

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["estoque_atual"]["competencia"]["id"],
            anterior.pk,
        )
        self.assertEqual(len(response.data["historico"]), 1)
        self.assertEqual(
            response.data["historico"][0]["competencia"],
            {"id": recente.pk, "ano": 2026, "mes": 8, "completa": False},
        )

    def test_importacao_parcial_nao_completa_mas_preserva_registro_no_historico(self):
        competencia = self.criar_competencia(2026, 8)
        self.completar_competencia(
            competencia,
            status_importacao=Importacao.Status.CONCLUIDA_PARCIAL,
        )
        self.criar_estoque(competencia, self.ups_a, "7.500")
        self.autenticar()

        response = self.client.get(self.url)

        self.assertIsNone(response.data["estoque_atual"])
        self.assertFalse(response.data["historico"][0]["competencia"]["completa"])
        self.assertEqual(
            response.data["historico"][0]["quantidade_consolidada_convencional"],
            "7.500",
        )

    def test_estoque_atual_soma_lotes_ups_e_exclui_nao_convencional_do_consolidado(self):
        competencia = self.criar_competencia(2026, 8)
        self.completar_competencia(competencia)
        self.criar_importacao(competencia, self.ups_nao_convencional)
        self.criar_estoque(competencia, self.ups_a, "1.125", "LOTE-A")
        self.criar_estoque(competencia, self.ups_a, "2.375")
        self.criar_estoque(competencia, self.ups_b, "3.500", "LOTE-B")
        self.criar_estoque(
            competencia,
            self.ups_nao_convencional,
            "50.125",
            "LOTE-NC",
        )
        self.autenticar()

        response = self.client.get(self.url)

        atual = response.data["estoque_atual"]
        self.assertEqual(atual["quantidade_consolidada_convencional"], "7.000")
        self.assertEqual(len(atual["por_ups"]), 3)
        ups_a = next(item for item in atual["por_ups"] if item["ups"]["id"] == self.ups_a.pk)
        self.assertEqual(ups_a["quantidade_total"], "3.500")
        self.assertEqual(len(ups_a["registros"]), 2)
        self.assertEqual(ups_a["registros"][0]["lote"]["codigo_lote"], "LOTE-A")
        self.assertIsNone(ups_a["registros"][1]["lote"])
        nao_convencional = next(
            item
            for item in atual["por_ups"]
            if item["ups"]["id"] == self.ups_nao_convencional.pk
        )
        self.assertFalse(nao_convencional["ups"]["compoe_estoque_convencional"])
        self.assertEqual(nao_convencional["quantidade_total"], "50.125")

    def test_historico_e_ordenado_e_nao_duplica_estoque_atual(self):
        atual = self.criar_competencia(2026, 3)
        janeiro = self.criar_competencia(2026, 1)
        dezembro = self.criar_competencia(2025, 12)
        self.completar_competencia(atual)
        for competencia, quantidade in (
            (atual, "3.000"),
            (janeiro, "1.000"),
            (dezembro, "12.000"),
        ):
            if competencia != atual:
                self.criar_importacao(
                    competencia,
                    self.ups_a,
                    Importacao.Status.CONCLUIDA_PARCIAL,
                )
            self.criar_estoque(competencia, self.ups_a, quantidade)
        self.autenticar()

        response = self.client.get(self.url)

        self.assertEqual(response.data["estoque_atual"]["competencia"]["id"], atual.pk)
        self.assertEqual(
            [item["competencia"]["id"] for item in response.data["historico"]],
            [janeiro.pk, dezembro.pk],
        )

    def test_filtro_de_estoque_por_medicamento(self):
        outro = Medicamento.objects.create(
            codigo_gmus="MED-HIST-2",
            descricao="OUTRO MEDICAMENTO",
            unidade="FRASC",
        )
        competencia = self.criar_competencia(2026, 8)
        self.completar_competencia(competencia)
        estoque_esperado = self.criar_estoque(competencia, self.ups_a, "1.000")
        self.criar_estoque(
            competencia,
            self.ups_b,
            "2.000",
            medicamento=outro,
        )
        self.autenticar()

        response = self.client.get(
            reverse("estoque-list"),
            {"medicamento": self.medicamento.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [estoque_esperado.pk])

    def test_api_publica_nao_expoe_campos_administrativos(self):
        response = self.client.get(
            reverse("public-medicamento-list"),
            {"search": self.medicamento.codigo_gmus},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data[0]),
            {"codigo_gmus", "descricao", "unidade", "disponibilidade"},
        )

    def test_numero_de_queries_e_constante_com_varios_registros(self):
        competencia = self.criar_competencia(2026, 8)
        self.completar_competencia(competencia)
        for indice in range(10):
            self.criar_estoque(
                competencia,
                self.ups_a,
                "1.001",
                f"LOTE-{indice}",
            )
        self.autenticar()

        with self.assertNumQueries(4):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["estoque_atual"]["quantidade_consolidada_convencional"],
            "10.010",
        )
