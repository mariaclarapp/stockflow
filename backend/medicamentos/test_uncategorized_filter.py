from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Classificacao, Medicamento, SubgrupoGmus


class UncategorizedMedicationFilterTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username="staff_sem_categoria",
            password="senha-ficticia",
            is_staff=True,
        )
        cls.manipulado = Classificacao.objects.create(nome="MANIPULADO")
        cls.categoria_manual = Classificacao.objects.create(nome="USO CONTINUO")
        cls.subgrupo = SubgrupoGmus.objects.create(
            codigo_gmus=82,
            nome="PSICOTROPICOS",
        )
        cls.sem_categoria = Medicamento.objects.create(
            codigo_gmus="SEM-CAT-1",
            descricao="DULOXETINA SEM CATEGORIA",
        )
        cls.apenas_manipulado = Medicamento.objects.create(
            codigo_gmus="SEM-CAT-2",
            descricao="DULOXETINA MANIPULADA",
        )
        cls.apenas_manipulado.classificacoes.add(cls.manipulado)
        cls.com_categoria_manual = Medicamento.objects.create(
            codigo_gmus="COM-CAT-1",
            descricao="MEDICAMENTO COM CATEGORIA MANUAL",
        )
        cls.com_categoria_manual.classificacoes.add(cls.categoria_manual)
        cls.com_subgrupo = Medicamento.objects.create(
            codigo_gmus="COM-SUB-1",
            descricao="MEDICAMENTO COM SUBGRUPO",
            subgrupo_gmus=cls.subgrupo,
        )
        cls.url = reverse("medicamento-list")

    def setUp(self):
        self.client.force_authenticate(self.staff)

    def test_returns_null_subgroup_without_common_manual_category(self):
        response = self.client.get(self.url, {"sem_categoria": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data},
            {self.sem_categoria.pk, self.apenas_manipulado.pk},
        )

    def test_manipulated_tag_does_not_make_medication_categorized(self):
        response = self.client.get(
            self.url,
            {"sem_categoria": "true", "search": "MANIPULADA"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [self.apenas_manipulado.pk],
        )
        self.assertEqual(response.data[0]["classificacoes"][0]["nome"], "MANIPULADO")

    def test_common_manual_category_and_subgroup_are_excluded(self):
        response = self.client.get(self.url, {"sem_categoria": "true"})
        ids = {item["id"] for item in response.data}

        self.assertNotIn(self.com_categoria_manual.pk, ids)
        self.assertNotIn(self.com_subgrupo.pk, ids)

    def test_rejects_incompatible_category_filters(self):
        subgroup_response = self.client.get(
            self.url,
            {"sem_categoria": "true", "subgrupo": self.subgrupo.pk},
        )
        classification_response = self.client.get(
            self.url,
            {
                "sem_categoria": "true",
                "classificacao": self.categoria_manual.pk,
            },
        )

        self.assertEqual(subgroup_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            classification_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("sem_categoria", subgroup_response.data)

    def test_query_count_is_constant(self):
        with self.assertNumQueries(4):
            response = self.client.get(self.url, {"sem_categoria": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
