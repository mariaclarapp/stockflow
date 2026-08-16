from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus


class PublicMedicineApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subgrupo = SubgrupoGmus.objects.create(
            codigo_gmus=10,
            nome="SUBGRUPO INTERNO",
        )
        cls.principio_ativo = PrincipioAtivo.objects.create(nome="Dipirona")
        cls.classificacao = Classificacao.objects.create(nome="CLASSIFICACAO INTERNA")
        cls.presentations = [
            Medicamento.objects.create(
                codigo_gmus="115.1",
                descricao="DIPIRONA / 500MG",
                unidade="COMPR",
                subgrupo_gmus=cls.subgrupo,
            ),
            Medicamento.objects.create(
                codigo_gmus="115.2",
                descricao="DIPIRONA / 500MG/ML",
                unidade="FRASC",
                subgrupo_gmus=cls.subgrupo,
            ),
            Medicamento.objects.create(
                codigo_gmus="115.3",
                descricao="DIPIRONA / 500MG/ML - 2ML AMPOLA",
                unidade="AMPOL",
                subgrupo_gmus=cls.subgrupo,
            ),
        ]
        for medicine in cls.presentations:
            medicine.principios_ativos.add(cls.principio_ativo)
            medicine.classificacoes.add(cls.classificacao)
        cls.other_medicine = Medicamento.objects.create(
            codigo_gmus="200.1",
            descricao="AMOXICILINA / 500MG",
            unidade="CAPS",
        )
        cls.admin_user = get_user_model().objects.create_user(
            username="farmaceutica_protecao_admin",
            password="senha-ficticia",
        )
        cls.public_url = reverse("public-medicamento-list")
        cls.admin_url = reverse("medicamento-list")

    def search(self, term):
        return self.client.get(self.public_url, {"search": term})

    def test_public_list_allows_anonymous_access(self):
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_public_searches_partially_by_description(self):
        response = self.search("pirona")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_public_search_is_case_insensitive(self):
        response = self.search("dIpIrOnA")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["codigo_gmus"] for item in response.data},
            {"115.1", "115.2", "115.3"},
        )

    def test_public_searches_by_gmus_code(self):
        response = self.search("115.2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["codigo_gmus"], "115.2")
        self.assertEqual(len(response.data), 1)

    def test_public_returns_presentations_separately(self):
        response = self.search("dipirona")

        self.assertEqual(
            [
                (item["codigo_gmus"], item["descricao"], item["unidade"])
                for item in response.data
            ],
            [
                ("115.1", "DIPIRONA / 500MG", "COMPR"),
                ("115.2", "DIPIRONA / 500MG/ML", "FRASC"),
                ("115.3", "DIPIRONA / 500MG/ML - 2ML AMPOLA", "AMPOL"),
            ],
        )

    def test_public_search_without_results_returns_empty_list(self):
        response = self.search("termo-inexistente")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_public_response_omits_all_administrative_fields(self):
        response = self.search("115.1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data[0]),
            {"codigo_gmus", "descricao", "unidade"},
        )
        forbidden_fields = {
            "id",
            "ups",
            "quantidade",
            "quantidade_total",
            "lote",
            "validade",
            "competencia",
            "importacao",
            "usuario",
            "subgrupo_gmus",
            "principios_ativos",
            "classificacoes",
            "disponibilidade",
        }
        self.assertTrue(forbidden_fields.isdisjoint(response.data[0]))

    def test_administrative_endpoint_remains_protected(self):
        response = self.client.get(self.admin_url)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
