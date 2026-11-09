from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import SaldoEstoque
from importacoes.models import Importacao

from .models import Classificacao, Medicamento


class AdminMedicineSearchApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="farmaceutica_pesquisa",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.presentations = [
            Medicamento.objects.create(
                codigo_gmus="115.1",
                descricao="DIPIRONA / 500MG",
                unidade="COMPR",
            ),
            Medicamento.objects.create(
                codigo_gmus="115.2",
                descricao="DIPIRONA / 500MG/ML",
                unidade="FRASC",
            ),
            Medicamento.objects.create(
                codigo_gmus="115.3",
                descricao="DIPIRONA / 500MG/ML - 2ML AMPOLA",
                unidade="AMPOL",
            ),
        ]
        cls.other_medicine = Medicamento.objects.create(
            codigo_gmus="200.1",
            descricao="AMOXICILINA / 500MG",
            unidade="CAPS",
        )
        cls.tag = Classificacao.objects.create(nome="TAG PESQUISA")
        cls.presentations[0].classificacoes.add(cls.tag)
        ups = Ups.objects.create(
            codigo_gmus="UPS-PESQUISA",
            id_unidade_gmus="1",
            nome="UPS PESQUISA",
        )
        competencia = Competencia.objects.create(ano=2031, mes=2)
        importacao = Importacao.objects.create(
            nome_arquivo="estoque-pesquisa.csv",
            tipo_relatorio="estoque",
            data_importacao=timezone.now(),
            status=Importacao.Status.CONCLUIDA,
            usuario=cls.user,
            competencia=competencia,
            ups=ups,
        )
        SaldoEstoque.objects.bulk_create(
            [
                SaldoEstoque(
                    medicamento=medicamento,
                    ups=ups,
                    competencia=competencia,
                    importacao=importacao,
                    quantidade="0.000",
                )
                for medicamento in (*cls.presentations, cls.other_medicine)
            ]
        )
        cls.url = reverse("medicamento-list")

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def search(self, term):
        return self.client.get(self.url, {"search": term})

    def test_searches_partially_by_description(self):
        self.authenticate()

        response = self.search("pirona")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertTrue(
            all("DIPIRONA" in item["descricao"] for item in response.data)
        )

    def test_description_search_is_case_insensitive(self):
        self.authenticate()

        response = self.search("dIpIrOnA")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["codigo_gmus"] for item in response.data},
            {"115.1", "115.2", "115.3"},
        )

    def test_searches_by_gmus_code(self):
        self.authenticate()

        response = self.search("115.2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["codigo_gmus"], "115.2")

    def test_returns_presentations_as_separate_medicines(self):
        self.authenticate()

        response = self.search("dipirona")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
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

    def test_search_without_results_returns_empty_list(self):
        self.authenticate()

        response = self.search("termo-inexistente")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_search_requires_authentication(self):
        response = self.search("dipirona")

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_request_without_search_returns_normal_list(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(
            {item["codigo_gmus"] for item in response.data},
            {"115.1", "115.2", "115.3", "200.1"},
        )

    def test_filters_by_tag(self):
        self.authenticate()

        response = self.client.get(self.url, {"tag": self.tag.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["codigo_gmus"] for item in response.data],
            ["115.1"],
        )

    def test_combines_tag_with_search(self):
        self.authenticate()

        response = self.client.get(
            self.url,
            {"tag": self.tag.pk, "search": "dipirona"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["codigo_gmus"] for item in response.data],
            ["115.1"],
        )
