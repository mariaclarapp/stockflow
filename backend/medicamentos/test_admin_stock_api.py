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


class AdministrativeMedicationStockApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff_saldo_medicamentos",
            password="senha-ficticia",
            is_staff=True,
        )
        self.ups_convencional_a = Ups.objects.create(
            codigo_gmus="UPS-SALDO",
            id_unidade_gmus="A",
            nome="UPS CONVENCIONAL A",
        )
        self.ups_convencional_b = Ups.objects.create(
            codigo_gmus="UPS-SALDO",
            id_unidade_gmus="B",
            nome="UPS CONVENCIONAL B",
        )
        self.ups_nao_convencional = Ups.objects.create(
            codigo_gmus="UPS-SALDO",
            id_unidade_gmus="C",
            nome="UPS NAO CONVENCIONAL",
            compoe_estoque_convencional=False,
        )
        self.competencia = Competencia.objects.create(ano=2030, mes=6)
        self.importacoes = {
            ups.pk: Importacao.objects.create(
                nome_arquivo=f"inventario-{ups.id_unidade_gmus}.csv",
                tipo_relatorio="inventario",
                data_importacao=timezone.now(),
                status=Importacao.Status.CONCLUIDA,
                usuario=self.staff,
                competencia=self.competencia,
                ups=ups,
            )
            for ups in (
                self.ups_convencional_a,
                self.ups_convencional_b,
                self.ups_nao_convencional,
            )
        }
        self.medicamento = Medicamento.objects.create(
            codigo_gmus="SALDO-1",
            descricao="MEDICAMENTO COM SALDO",
            unidade="COMPR",
        )
        self.sem_estoque = Medicamento.objects.create(
            codigo_gmus="SALDO-2",
            descricao="MEDICAMENTO SEM ESTOQUE",
            unidade="COMPR",
        )
        self.url = reverse("medicamento-list")
        self.client.force_authenticate(self.staff)

    def criar_estoque(self, ups, quantidade, lote, medicamento=None):
        medicamento = medicamento or self.medicamento
        lote_obj = Lote.objects.create(
            medicamento=medicamento,
            codigo_lote=lote,
            data_validade=date(2031, 12, 31),
        )
        return Estoque.objects.create(
            medicamento=medicamento,
            ups=ups,
            competencia=self.competencia,
            lote=lote_obj,
            importacao=self.importacoes[ups.pk],
            quantidade=quantidade,
        )

    def obter_itens(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {item["codigo_gmus"]: item for item in response.data}

    def test_list_sums_stock_only_from_conventional_ups(self):
        self.criar_estoque(self.ups_convencional_a, "2.500", "LOTE-A1")

        itens = self.obter_itens()

        self.assertEqual(itens["SALDO-1"]["quantidade_estoque_total"], "2.500")

    def test_list_sums_stock_from_pharmacy_and_caf(self):
        self.criar_estoque(self.ups_convencional_a, "2.500", "LOTE-A1")
        self.criar_estoque(self.ups_convencional_b, "4.500", "LOTE-B1")

        itens = self.obter_itens()

        self.assertEqual(itens["SALDO-1"]["quantidade_estoque_total"], "7.000")

    def test_list_includes_stock_only_from_manipulation_ups(self):
        self.criar_estoque(self.ups_convencional_a, "0.000", "LOTE-A-ZERO")
        self.criar_estoque(self.ups_convencional_b, "0.000", "LOTE-B-ZERO")
        self.criar_estoque(
            self.ups_nao_convencional,
            "1770.000",
            "LOTE-MANIPULADO",
        )

        itens = self.obter_itens()

        self.assertEqual(itens["SALDO-1"]["quantidade_estoque_total"], "1770.000")

    def test_detail_includes_total_stock_from_manipulation_ups(self):
        self.criar_estoque(self.ups_convencional_a, "0.000", "LOTE-A-ZERO")
        self.criar_estoque(self.ups_convencional_b, "0.000", "LOTE-B-ZERO")
        self.criar_estoque(
            self.ups_nao_convencional,
            "1770.000",
            "LOTE-MANIPULADO",
        )

        response = self.client.get(
            reverse("medicamento-detail", args=[self.medicamento.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["quantidade_estoque_total"], "1770.000")

    def test_list_sums_multiple_lots_across_all_participating_ups(self):
        self.criar_estoque(self.ups_convencional_a, "2.500", "LOTE-A1")
        self.criar_estoque(self.ups_convencional_a, "3.000", "LOTE-A2")
        self.criar_estoque(self.ups_convencional_b, "4.500", "LOTE-B1")
        self.criar_estoque(self.ups_nao_convencional, "100.000", "LOTE-C1")

        itens = self.obter_itens()

        self.assertEqual(itens["SALDO-1"]["quantidade_estoque_total"], "110.000")

    def test_list_returns_zero_for_medicine_without_stock(self):
        itens = self.obter_itens()

        self.assertEqual(itens["SALDO-2"]["quantidade_estoque_total"], "0.000")

    def test_list_returns_null_without_complete_competence(self):
        Importacao.objects.filter(ups=self.ups_nao_convencional).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data[0]["quantidade_estoque_total"])
        self.assertIsNone(response.data[1]["quantidade_estoque_total"])

    def test_list_query_count_is_constant_for_multiple_medications(self):
        Medicamento.objects.bulk_create(
            [
                Medicamento(
                    codigo_gmus=f"SALDO-EXTRA-{indice}",
                    descricao=f"MEDICAMENTO EXTRA {indice}",
                )
                for indice in range(10)
            ]
        )

        with self.assertNumQueries(5):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 12)

    def test_classification_filter_keeps_query_count_constant(self):
        categoria = Classificacao.objects.create(nome="CATEGORIA TESTE")
        self.medicamento.classificacoes.add(categoria)

        with self.assertNumQueries(5):
            response = self.client.get(
                self.url,
                {"classificacao": categoria.pk},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["codigo_gmus"] for item in response.data],
            [self.medicamento.codigo_gmus],
        )

    def test_ids_filter_returns_one_medication(self):
        response = self.client.get(self.url, {"ids": str(self.medicamento.pk)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.medicamento.pk],
        )

    def test_ids_filter_preserves_requested_order_for_multiple_medications(self):
        response = self.client.get(
            self.url,
            {"ids": f"{self.sem_estoque.pk},{self.medicamento.pk}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.sem_estoque.pk, self.medicamento.pk],
        )

    def test_ids_filter_removes_repeated_ids(self):
        response = self.client.get(
            self.url,
            {"ids": f"{self.medicamento.pk},{self.medicamento.pk}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.medicamento.pk)

    def test_ids_filter_ignores_nonexistent_id(self):
        response = self.client.get(
            self.url,
            {"ids": f"999999,{self.medicamento.pk}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.medicamento.pk],
        )

    def test_ids_filter_rejects_invalid_format(self):
        response = self.client.get(self.url, {"ids": f"{self.medicamento.pk},abc"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ids", response.data)

    def test_ids_filter_rejects_more_than_fifty_unique_ids(self):
        ids = [self.medicamento.pk, self.sem_estoque.pk]
        ids.extend(
            Medicamento.objects.create(
                codigo_gmus=f"SELECAO-{indice}",
                descricao=f"MEDICAMENTO SELECAO {indice}",
            ).pk
            for indice in range(49)
        )

        response = self.client.get(
            self.url,
            {"ids": ",".join(str(item) for item in ids)},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ids", response.data)

    def test_ids_filter_requires_staff_user(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url, {"ids": str(self.medicamento.pk)})

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_ids_filter_rejects_authenticated_non_staff_user(self):
        user = get_user_model().objects.create_user(
            username="usuario_sem_acesso_a_selecao",
            password="senha-ficticia",
            is_staff=False,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url, {"ids": str(self.medicamento.pk)})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ids_filter_combines_with_search_and_classification(self):
        categoria = Classificacao.objects.create(nome="CATEGORIA COMBINADA")
        self.medicamento.classificacoes.add(categoria)

        response = self.client.get(
            self.url,
            {
                "ids": f"{self.sem_estoque.pk},{self.medicamento.pk}",
                "search": "COM SALDO",
                "classificacao": categoria.pk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.medicamento.pk],
        )

    def test_ids_filter_keeps_serializer_relations_and_total_stock(self):
        subgrupo = SubgrupoGmus.objects.create(codigo_gmus=91, nome="SUBGRUPO TESTE")
        classificacao = Classificacao.objects.create(nome="CLASSIFICACAO SELECAO")
        self.medicamento.subgrupo_gmus = subgrupo
        self.medicamento.save(update_fields=["subgrupo_gmus"])
        self.medicamento.classificacoes.add(classificacao)
        self.criar_estoque(self.ups_convencional_a, "8.500", "LOTE-SELECAO")

        response = self.client.get(self.url, {"ids": str(self.medicamento.pk)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["subgrupo_gmus"]["id"], subgrupo.pk)
        self.assertEqual(response.data[0]["classificacoes"][0]["id"], classificacao.pk)
        self.assertEqual(response.data[0]["quantidade_estoque_total"], "8.500")

    def test_ids_filter_query_count_is_constant(self):
        extras = [
            Medicamento.objects.create(
                codigo_gmus=f"IDS-QUERY-{indice}",
                descricao=f"MEDICAMENTO IDS QUERY {indice}",
            )
            for indice in range(8)
        ]
        ids = [
            self.medicamento.pk,
            self.sem_estoque.pk,
            *[item.pk for item in extras],
        ]

        with self.assertNumQueries(5):
            response = self.client.get(
                self.url,
                {"ids": ",".join(str(item) for item in ids)},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)

    def test_public_api_does_not_expose_administrative_quantity(self):
        response = self.client.get(reverse("public-medicamento-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("quantidade_estoque_total", response.data[0])
        self.assertNotIn("quantidade_estoque_atual", response.data[0])

    def test_manipulated_public_availability_remains_independent_from_total(self):
        classificacao = Classificacao.objects.create(nome="MANIPULADO", ativo=True)
        self.medicamento.classificacoes.add(classificacao)
        self.criar_estoque(
            self.ups_nao_convencional,
            "1770.000",
            "LOTE-MANIPULADO",
        )

        admin_item = self.obter_itens()["SALDO-1"]
        public_response = self.client.get(
            reverse("public-medicamento-list"),
            {"search": "SALDO-1"},
        )

        self.assertEqual(admin_item["quantidade_estoque_total"], "1770.000")
        self.assertEqual(
            public_response.data[0]["disponibilidade"],
            "Disponível sob manipulação, confirmar disponibilidade",
        )
