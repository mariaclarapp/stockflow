from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from importacoes.models import Importacao
from medicamentos.models import Medicamento, SubgrupoGmus

from .models import Estoque


class AdminStructuredFiltersApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="farmaceutica_filtros",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.subgrupo_a = SubgrupoGmus.objects.create(
            codigo_gmus=10,
            nome="SUBGRUPO A",
        )
        cls.subgrupo_b = SubgrupoGmus.objects.create(
            codigo_gmus=20,
            nome="SUBGRUPO B",
        )
        cls.dipirona_comprimido = Medicamento.objects.create(
            codigo_gmus="115.1",
            descricao="DIPIRONA / 500MG",
            unidade="COMPR",
            subgrupo_gmus=cls.subgrupo_a,
        )
        cls.dipirona_gotas = Medicamento.objects.create(
            codigo_gmus="115.2",
            descricao="DIPIRONA / 500MG/ML",
            unidade="FRASC",
            subgrupo_gmus=cls.subgrupo_b,
        )
        cls.amoxicilina = Medicamento.objects.create(
            codigo_gmus="200.1",
            descricao="AMOXICILINA / 500MG",
            unidade="CAPS",
            subgrupo_gmus=cls.subgrupo_a,
        )
        cls.ibuprofeno = Medicamento.objects.create(
            codigo_gmus="300.1",
            descricao="IBUPROFENO / 600MG",
            unidade="COMPR",
            subgrupo_gmus=cls.subgrupo_a,
        )
        cls.ups_a = Ups.objects.create(
            codigo_gmus="2780046", id_unidade_gmus="9", nome="UPS A"
        )
        cls.ups_b = Ups.objects.create(
            codigo_gmus="2780046", id_unidade_gmus="10", nome="UPS B"
        )
        cls.competencia_a = Competencia.objects.create(ano=2026, mes=8)
        cls.competencia_b = Competencia.objects.create(ano=2026, mes=9)

        importacao_a = cls.create_importacao(cls.ups_a, cls.competencia_a, "a")
        importacao_b = cls.create_importacao(cls.ups_b, cls.competencia_a, "b")
        importacao_c = cls.create_importacao(cls.ups_a, cls.competencia_b, "c")

        cls.create_estoque(cls.dipirona_comprimido, importacao_a)
        cls.create_estoque(cls.dipirona_gotas, importacao_a)
        cls.create_estoque(cls.amoxicilina, importacao_b)
        cls.create_estoque(cls.ibuprofeno, importacao_c)

        cls.medicamentos_url = reverse("medicamento-list")
        cls.estoques_url = reverse("estoque-list")

    @classmethod
    def create_importacao(cls, ups, competencia, suffix):
        return Importacao.objects.create(
            nome_arquivo=f"inventario-{suffix}.csv",
            hash_arquivo=suffix * 64,
            tipo_relatorio="inventario",
            data_importacao=timezone.now(),
            status=Importacao.Status.CONCLUIDA,
            usuario=cls.user,
            competencia=competencia,
            ups=ups,
        )

    @classmethod
    def create_estoque(cls, medicamento, importacao):
        return Estoque.objects.create(
            medicamento=medicamento,
            ups=importacao.ups,
            competencia=importacao.competencia,
            lote=None,
            importacao=importacao,
            quantidade=Decimal("10.000"),
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_filters_stock_by_unambiguous_stockflow_ups_id(self):
        self.authenticate()

        response = self.client.get(self.estoques_url, {"ups": self.ups_a.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertTrue(
            all(item["ups"]["id"] == self.ups_a.pk for item in response.data)
        )

    def test_rejects_ambiguous_shared_ups_code_filter(self):
        self.authenticate()

        response = self.client.get(
            self.estoques_url,
            {"ups_codigo": "2780046"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ups_codigo", str(response.data))

    def test_filters_stock_by_competence(self):
        self.authenticate()

        response = self.client.get(
            self.estoques_url,
            {"competencia": self.competencia_a.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertTrue(
            all(
                item["competencia"]["id"] == self.competencia_a.pk
                for item in response.data
            )
        )

    def test_filters_medicines_by_subgroup(self):
        self.authenticate()

        response = self.client.get(
            self.medicamentos_url,
            {"subgrupo": self.subgrupo_a.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["codigo_gmus"] for item in response.data},
            {"115.1", "200.1", "300.1"},
        )

    def test_combines_stock_filters(self):
        self.authenticate()

        response = self.client.get(
            self.estoques_url,
            {
                "ups": self.ups_a.pk,
                "competencia": self.competencia_a.pk,
                "subgrupo": self.subgrupo_a.pk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["medicamento"]["codigo_gmus"],
            "115.1",
        )

    def test_combines_search_with_subgroup_filter(self):
        self.authenticate()

        response = self.client.get(
            self.medicamentos_url,
            {"search": "dipirona", "subgrupo": self.subgrupo_a.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["codigo_gmus"], "115.1")

    def test_combined_filters_can_return_no_results(self):
        self.authenticate()

        response = self.client.get(
            self.estoques_url,
            {
                "ups": self.ups_b.pk,
                "competencia": self.competencia_b.pk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filters_require_authentication(self):
        requests = [
            (self.estoques_url, {"ups": self.ups_a.pk}),
            (self.medicamentos_url, {"subgrupo": self.subgrupo_a.pk}),
        ]

        for url, params in requests:
            with self.subTest(url=url):
                response = self.client.get(url, params)
                self.assertIn(
                    response.status_code,
                    [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                )
