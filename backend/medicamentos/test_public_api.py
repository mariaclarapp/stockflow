from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from importacoes.models import Importacao

from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .services import DisponibilidadePublicaService


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
            {"codigo_gmus", "descricao", "unidade", "disponibilidade"},
        )
        self.assertEqual(
            response.data[0]["disponibilidade"],
            "Disponibilidade não informada",
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
        }
        self.assertTrue(forbidden_fields.isdisjoint(response.data[0]))

    def test_administrative_endpoint_remains_protected(self):
        response = self.client.get(self.admin_url)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class PublicMedicineAvailabilityTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="usuario_disponibilidade_teste",
            password="senha-ficticia",
        )
        self.ups_a = Ups.objects.create(
            codigo_gmus="UPS-A",
            id_unidade_gmus="A",
            nome="UNIDADE CONVENCIONAL A",
        )
        self.ups_b = Ups.objects.create(
            codigo_gmus="UPS-B",
            id_unidade_gmus="B",
            nome="UNIDADE CONVENCIONAL B",
        )
        self.url = reverse("public-medicamento-list")

    def create_medicine(self, code="MED-1", description="MEDICAMENTO TESTE"):
        return Medicamento.objects.create(
            codigo_gmus=code,
            descricao=description,
            unidade="COMPR",
        )

    def create_competence(self, year, month):
        return Competencia.objects.create(ano=year, mes=month)

    def create_import(
        self,
        competence,
        ups,
        import_status=Importacao.Status.CONCLUIDA,
        report_type="inventario",
    ):
        return Importacao.objects.create(
            nome_arquivo=f"inventario-{competence.ano}-{competence.mes}-{ups.pk}.csv",
            hash_arquivo="",
            tipo_relatorio=report_type,
            data_importacao=timezone.now(),
            status=import_status,
            usuario=self.user,
            competencia=competence,
            ups=ups,
        )

    def complete_competence(
        self,
        competence,
        import_status=Importacao.Status.CONCLUIDA,
    ):
        return {
            ups.pk: self.create_import(competence, ups, import_status)
            for ups in (self.ups_a, self.ups_b)
        }

    def create_stock(
        self,
        medicine,
        competence,
        ups,
        quantity,
        lot_code=None,
    ):
        lot = None
        if lot_code:
            lot = Lote.objects.create(
                medicamento=medicine,
                codigo_lote=lot_code,
                data_validade=date(2028, 12, 31),
            )
        importacao = Importacao.objects.get(
            competencia=competence,
            ups=ups,
            tipo_relatorio="inventario",
        )
        return Estoque.objects.create(
            medicamento=medicine,
            ups=ups,
            competencia=competence,
            lote=lot,
            importacao=importacao,
            quantidade=Decimal(quantity),
        )

    def get_public_medicine(self, medicine):
        response = self.client.get(self.url, {"search": medicine.codigo_gmus})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        return response.data[0]

    def test_active_manipulated_with_zero_stock_has_absolute_precedence(self):
        medicine = self.create_medicine()
        manipulated = Classificacao.objects.create(nome="MANIPULADO", ativo=True)
        medicine.classificacoes.add(manipulated)
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "0")

        result = self.get_public_medicine(medicine)

        self.assertEqual(
            result["disponibilidade"],
            "Disponível sob manipulação, confirmar disponibilidade",
        )

    def test_active_manipulated_with_positive_conventional_stock_keeps_precedence(self):
        medicine = self.create_medicine()
        manipulated = Classificacao.objects.create(nome="MANIPULADO", ativo=True)
        medicine.classificacoes.add(manipulated)
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "25")

        result = self.get_public_medicine(medicine)

        self.assertEqual(
            result["disponibilidade"],
            "Disponível sob manipulação, confirmar disponibilidade",
        )

    def test_inactive_manipulated_tag_is_ignored(self):
        medicine = self.create_medicine()
        manipulated = Classificacao.objects.create(nome="MANIPULADO", ativo=False)
        medicine.classificacoes.add(manipulated)
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_conventional_medicine_with_positive_stock_is_available(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "1")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Disponível")

    def test_conventional_medicine_with_zero_stock_is_unavailable(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "0")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_sums_all_lots_for_the_medicine(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "2", "LOTE-A")
        self.create_stock(medicine, competence, self.ups_a, "3", "LOTE-B")

        annotated = DisponibilidadePublicaService.anotar_disponibilidade(
            Medicamento.objects.filter(pk=medicine.pk)
        ).get()

        self.assertEqual(annotated.saldo_convencional, Decimal("5"))
        self.assertEqual(annotated.disponibilidade, "Disponível")

    def test_sums_stock_from_multiple_conventional_ups(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "4")
        self.create_stock(medicine, competence, self.ups_b, "6")

        annotated = DisponibilidadePublicaService.anotar_disponibilidade(
            Medicamento.objects.filter(pk=medicine.pk)
        ).get()

        self.assertEqual(annotated.saldo_convencional, Decimal("10"))

    def test_uses_the_most_recent_complete_competence(self):
        medicine = self.create_medicine()
        older = self.create_competence(2026, 7)
        latest = self.create_competence(2026, 8)
        self.complete_competence(older)
        self.complete_competence(latest)
        self.create_stock(medicine, older, self.ups_a, "10")
        self.create_stock(medicine, latest, self.ups_a, "0")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_falls_back_when_the_latest_competence_is_incomplete(self):
        medicine = self.create_medicine()
        older = self.create_competence(2026, 7)
        latest = self.create_competence(2026, 8)
        self.complete_competence(older)
        self.create_stock(medicine, older, self.ups_a, "0")
        self.create_import(latest, self.ups_a)
        self.create_stock(medicine, latest, self.ups_a, "100")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_partial_imports_do_not_complete_competence(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(
            competence,
            import_status=Importacao.Status.CONCLUIDA_PARCIAL,
        )
        self.create_stock(medicine, competence, self.ups_a, "100")

        result = self.get_public_medicine(medicine)

        self.assertEqual(
            result["disponibilidade"],
            "Disponibilidade não informada",
        )

    def test_alert_imports_can_complete_competence(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(
            competence,
            import_status=Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )
        self.create_stock(medicine, competence, self.ups_a, "2")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Disponível")

    def test_medicine_absent_from_complete_competence_has_zero_stock(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_without_complete_competence_availability_is_not_informed(self):
        medicine = self.create_medicine()

        result = self.get_public_medicine(medicine)

        self.assertEqual(
            result["disponibilidade"],
            "Disponibilidade não informada",
        )

    def test_nonconventional_ups_stock_is_not_included(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        nonconventional_ups = Ups.objects.create(
            codigo_gmus="UPS-NAO-CONVENCIONAL",
            id_unidade_gmus="NC",
            nome="UNIDADE NAO CONVENCIONAL",
            participa_competencia=False,
            compoe_estoque_convencional=False,
        )
        self.create_import(competence, nonconventional_ups)
        self.create_stock(medicine, competence, nonconventional_ups, "50")

        result = self.get_public_medicine(medicine)

        self.assertEqual(result["disponibilidade"], "Indisponível")

    def test_public_response_does_not_expose_calculation_inputs(self):
        medicine = self.create_medicine()
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        self.create_stock(medicine, competence, self.ups_a, "8", "LOTE-PRIVADO")

        result = self.get_public_medicine(medicine)

        self.assertEqual(
            set(result),
            {"codigo_gmus", "descricao", "unidade", "disponibilidade"},
        )

    def test_public_list_uses_a_constant_number_of_queries(self):
        competence = self.create_competence(2026, 8)
        self.complete_competence(competence)
        for index in range(5):
            medicine = self.create_medicine(
                code=f"MED-{index}",
                description=f"MEDICAMENTO TESTE {index}",
            )
            self.create_stock(medicine, competence, self.ups_a, "1")

        with self.assertNumQueries(3):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
