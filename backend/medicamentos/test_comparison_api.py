from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from importacoes.models import Importacao

from .models import Classificacao, Medicamento, SubgrupoGmus


class MedicationComparisonApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username="staff_comparacao",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.non_staff = get_user_model().objects.create_user(
            username="usuario_comparacao",
            password="senha-ficticia",
        )
        cls.ups_farmacia = Ups.objects.create(
            codigo_gmus="UPS-COMP",
            id_unidade_gmus="9",
            nome="FARMACIA MUNICIPAL",
        )
        cls.ups_caf = Ups.objects.create(
            codigo_gmus="UPS-COMP",
            id_unidade_gmus="10",
            nome="CAF",
        )
        cls.ups_manipulacao = Ups.objects.create(
            codigo_gmus="UPS-COMP",
            id_unidade_gmus="19",
            nome="FARMACIA DE MANIPULACAO",
            compoe_estoque_convencional=False,
        )
        cls.competencia = Competencia.objects.create(ano=2032, mes=8)
        cls.importacoes = {
            ups.pk: Importacao.objects.create(
                nome_arquivo=f"comparacao-{ups.id_unidade_gmus}.csv",
                tipo_relatorio="inventario",
                data_importacao=timezone.now(),
                status=Importacao.Status.CONCLUIDA,
                usuario=cls.staff,
                competencia=cls.competencia,
                ups=ups,
            )
            for ups in (cls.ups_farmacia, cls.ups_caf, cls.ups_manipulacao)
        }
        cls.subgrupo = SubgrupoGmus.objects.create(
            codigo_gmus=81,
            nome="SUBGRUPO COMPARACAO",
        )
        cls.classificacao = Classificacao.objects.create(
            nome="CATEGORIA COMPARACAO",
            cor="#0B8178",
        )
        cls.medicamentos = [
            Medicamento.objects.create(
                codigo_gmus=f"COMP-{indice}",
                descricao=f"MEDICAMENTO COMPARACAO {indice}",
                unidade="COMPR",
                subgrupo_gmus=cls.subgrupo if indice == 1 else None,
            )
            for indice in range(1, 7)
        ]
        cls.medicamentos[0].classificacoes.add(cls.classificacao)
        cls.url = reverse("medicamento-comparacao")

    def setUp(self):
        self.client.force_authenticate(self.staff)

    def criar_estoque(self, medicamento, ups, quantidade, codigo_lote):
        lote = Lote.objects.create(
            medicamento=medicamento,
            codigo_lote=codigo_lote,
            data_validade=date(2033, 12, 31),
        )
        return Estoque.objects.create(
            medicamento=medicamento,
            ups=ups,
            competencia=self.competencia,
            lote=lote,
            importacao=self.importacoes[ups.pk],
            quantidade=quantidade,
        )

    def consultar(self, ids):
        return self.client.get(self.url, {"ids": ",".join(map(str, ids))})

    def test_returns_one_requested_medication(self):
        response = self.consultar([self.medicamentos[2].pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["medicamentos"]],
            [self.medicamentos[2].pk],
        )

    def test_returns_exactly_three_requested_medications_among_many(self):
        solicitados = [
            self.medicamentos[4].pk,
            self.medicamentos[0].pk,
            self.medicamentos[2].pk,
        ]

        response = self.consultar(solicitados)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["medicamentos"]],
            solicitados,
        )
        self.assertEqual(len(response.data["medicamentos"]), 3)

    def test_removes_repeated_ids_and_ignores_nonexistent_ids(self):
        medicamento = self.medicamentos[1]

        response = self.consultar([medicamento.pk, 999999, medicamento.pk])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["medicamentos"]],
            [medicamento.pk],
        )

    def test_accepts_fifty_medications_and_rejects_fifty_first(self):
        extras = [
            Medicamento.objects.create(
                codigo_gmus=f"COMP-LIMITE-{indice}",
                descricao=f"MEDICAMENTO LIMITE {indice}",
            )
            for indice in range(44)
        ]
        cinquenta_ids = [
            *[item.pk for item in self.medicamentos],
            *[item.pk for item in extras],
        ]

        response = self.consultar(cinquenta_ids)
        excedente = self.client.get(
            self.url,
            {"ids": ",".join(str(indice) for indice in range(1, 52))},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["medicamentos"]), 50)
        self.assertEqual(excedente.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ids", excedente.data)

    def test_aggregates_lots_and_returns_zero_for_missing_ups(self):
        medicamento = self.medicamentos[0]
        self.criar_estoque(medicamento, self.ups_farmacia, "2.000", "LOTE-F1")
        self.criar_estoque(medicamento, self.ups_farmacia, "3.000", "LOTE-F2")
        self.criar_estoque(medicamento, self.ups_manipulacao, "10.000", "LOTE-M1")

        response = self.consultar([medicamento.pk])
        item = response.data["medicamentos"][0]
        quantidades = {
            linha["ups_id"]: linha["quantidade"]
            for linha in item["estoque_por_ups"]
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["competencia"]["id"], self.competencia.pk)
        self.assertEqual(len(response.data["ups"]), 3)
        self.assertEqual(quantidades[self.ups_farmacia.pk], "5.000")
        self.assertEqual(quantidades[self.ups_caf.pk], "0.000")
        self.assertEqual(quantidades[self.ups_manipulacao.pk], "10.000")
        self.assertEqual(item["quantidade_estoque_total"], "15.000")

    def test_medication_without_stock_returns_zero_for_every_ups(self):
        response = self.consultar([self.medicamentos[3].pk])
        item = response.data["medicamentos"][0]

        self.assertEqual(item["quantidade_estoque_total"], "0.000")
        self.assertEqual(
            [linha["quantidade"] for linha in item["estoque_por_ups"]],
            ["0.000", "0.000", "0.000"],
        )

    def test_without_complete_competence_returns_uninformed_stock(self):
        Importacao.objects.filter(ups=self.ups_manipulacao).delete()

        response = self.consultar([self.medicamentos[0].pk])
        item = response.data["medicamentos"][0]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["competencia"])
        self.assertEqual(response.data["ups"], [])
        self.assertIsNone(item["quantidade_estoque_total"])
        self.assertEqual(item["estoque_por_ups"], [])

    def test_serializer_preserves_categories_needed_by_comparison(self):
        response = self.consultar([self.medicamentos[0].pk])
        item = response.data["medicamentos"][0]

        self.assertEqual(item["subgrupo_gmus"]["id"], self.subgrupo.pk)
        self.assertEqual(item["classificacoes"][0]["id"], self.classificacao.pk)

    def test_query_count_is_constant(self):
        ids = [item.pk for item in self.medicamentos]

        with self.assertNumQueries(5):
            response = self.consultar(ids)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["medicamentos"]), 6)

    def test_requires_staff_authorization(self):
        self.client.force_authenticate(self.non_staff)
        non_staff_response = self.consultar([self.medicamentos[0].pk])
        self.client.force_authenticate(user=None)
        anonymous_response = self.consultar([self.medicamentos[0].pk])

        self.assertEqual(non_staff_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            anonymous_response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
