from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from importacoes.models import Importacao
from medicamentos.models import (
    Classificacao,
    Medicamento,
    PrincipioAtivo,
    SubgrupoGmus,
)


class AdminReadOnlyApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="farmaceutica",
            password="senha-ficticia",
        )
        cls.subgrupo = SubgrupoGmus.objects.create(codigo_gmus=10, nome="Analgesicos")
        cls.principio_ativo = PrincipioAtivo.objects.create(nome="Dipirona")
        cls.classificacao = Classificacao.objects.create(
            nome="Essencial",
            cor="#2f855a",
            descricao="Classificacao ficticia para teste",
        )
        cls.medicamento = Medicamento.objects.create(
            codigo_gmus="115.1",
            descricao="Dipirona 500 mg comprimido",
            unidade="comprimido",
            subgrupo_gmus=cls.subgrupo,
        )
        cls.medicamento.principios_ativos.add(cls.principio_ativo)
        cls.medicamento.classificacoes.add(cls.classificacao)
        cls.medicamento_sem_subgrupo = Medicamento.objects.create(
            codigo_gmus="999.1",
            descricao="Medicamento sem subgrupo",
            unidade="frasco",
        )

        cls.ups = Ups.objects.create(codigo_gmus="CAF", nome="CAF")
        cls.competencia = Competencia.objects.create(mes=8, ano=2026)
        cls.importacao = Importacao.objects.create(
            nome_arquivo="inventario-ficticio.csv",
            tipo_relatorio="inventario",
            data_importacao=timezone.now(),
            status="processado",
            usuario=cls.user,
            competencia=cls.competencia,
            ups=cls.ups,
        )
        cls.lote = Lote.objects.create(
            medicamento=cls.medicamento,
            codigo_lote="L001",
            data_validade="2027-12-31",
        )
        cls.estoque = Estoque.objects.create(
            medicamento=cls.medicamento,
            ups=cls.ups,
            competencia=cls.competencia,
            lote=cls.lote,
            importacao=cls.importacao,
            quantidade=Decimal("123.456"),
        )
        cls.estoque_sem_lote = Estoque.objects.create(
            medicamento=cls.medicamento_sem_subgrupo,
            ups=cls.ups,
            competencia=cls.competencia,
            lote=None,
            importacao=cls.importacao,
            quantidade=Decimal("0.000"),
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_requests_cannot_access_admin_endpoints(self):
        endpoints = [
            "subgrupo-gmus-list",
            "principio-ativo-list",
            "classificacao-list",
            "medicamento-list",
            "ups-list",
            "competencia-list",
            "lote-list",
            "estoque-list",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertIn(
                    response.status_code,
                    [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                )

    def test_authenticated_user_can_get_all_admin_endpoints(self):
        self.authenticate()
        endpoints = [
            "subgrupo-gmus-list",
            "principio-ativo-list",
            "classificacao-list",
            "medicamento-list",
            "ups-list",
            "competencia-list",
            "lote-list",
            "estoque-list",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_removed_endpoints_are_not_registered(self):
        self.authenticate()

        for path in ["/api/importacoes/", "/api/localizacoes-estoque/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_endpoints_are_read_only(self):
        self.authenticate()
        list_endpoints = [
            "subgrupo-gmus-list",
            "principio-ativo-list",
            "classificacao-list",
            "medicamento-list",
            "ups-list",
            "competencia-list",
            "lote-list",
            "estoque-list",
        ]
        detail_endpoints = [
            ("subgrupo-gmus-detail", self.subgrupo.id),
            ("principio-ativo-detail", self.principio_ativo.id),
            ("classificacao-detail", self.classificacao.id),
            ("medicamento-detail", self.medicamento.id),
            ("ups-detail", self.ups.id),
            ("competencia-detail", self.competencia.id),
            ("lote-detail", self.lote.id),
            ("estoque-detail", self.estoque.id),
        ]

        for endpoint in list_endpoints:
            with self.subTest(method="POST", endpoint=endpoint):
                response = self.client.post(reverse(endpoint), {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        for endpoint, pk in detail_endpoints:
            url = reverse(endpoint, args=[pk])
            for method in ["put", "patch", "delete"]:
                with self.subTest(method=method.upper(), endpoint=endpoint):
                    response = getattr(self.client, method)(url, {}, format="json")
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                    )

    def test_medicamento_serialization_preserves_expected_fields(self):
        self.authenticate()

        response = self.client.get(reverse("medicamento-detail", args=[self.medicamento.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["codigo_gmus"], "115.1")
        self.assertEqual(response.data["descricao"], "Dipirona 500 mg comprimido")
        self.assertEqual(response.data["unidade"], "comprimido")
        self.assertEqual(response.data["subgrupo_gmus"]["codigo_gmus"], 10)
        self.assertEqual(response.data["subgrupo_gmus"]["nome"], "Analgesicos")
        self.assertEqual(response.data["principios_ativos"][0]["nome"], "Dipirona")
        self.assertEqual(response.data["classificacoes"][0]["nome"], "Essencial")

    def test_estoque_serialization_preserves_stock_and_import_traceability(self):
        self.authenticate()

        response = self.client.get(reverse("estoque-detail", args=[self.estoque.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["medicamento"]["codigo_gmus"], "115.1")
        self.assertEqual(response.data["ups"]["codigo_gmus"], "CAF")
        self.assertEqual(response.data["competencia"]["mes"], 8)
        self.assertEqual(response.data["competencia"]["ano"], 2026)
        self.assertEqual(response.data["lote"]["codigo_lote"], "L001")
        self.assertNotIn("localizacao", response.data)
        self.assertEqual(response.data["quantidade"], "123.456")
        self.assertEqual(response.data["importacao"]["nome_arquivo"], "inventario-ficticio.csv")
        self.assertEqual(response.data["importacao"]["tipo_relatorio"], "inventario")
        self.assertEqual(response.data["importacao"]["status"], "processado")
        self.assertEqual(response.data["importacao"]["competencia"]["ano"], 2026)
        self.assertEqual(response.data["importacao"]["ups"]["codigo_gmus"], "CAF")
        self.assertEqual(response.data["importacao"]["usuario"], "farmaceutica")

    def test_optional_lote_is_serialized_as_null(self):
        self.authenticate()

        response = self.client.get(
            reverse("estoque-detail", args=[self.estoque_sem_lote.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["lote"])

    def test_optional_subgrupo_is_serialized_as_null(self):
        self.authenticate()

        response = self.client.get(
            reverse("medicamento-detail", args=[self.medicamento_sem_subgrupo.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["subgrupo_gmus"])
