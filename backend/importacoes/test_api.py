from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from medicamentos.models import Medicamento, SubgrupoGmus

from .models import Importacao


class InventoryUploadApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="farmaceutica_upload_teste",
            password="senha-ficticia",
            is_staff=True,
        )
        self.url = reverse("inventory-import-upload")

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def csv_upload(
        self,
        name="inventario-ficticio.csv",
        description="MEDICAMENTO TESTE",
        quantity="10",
        extra_rows=None,
    ):
        rows = [
            "Filtros: Compet\u00eancia: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Nao. Imp. Inativo? Nao. Ordenado por: Codigo.,,,,,,,,,,,,,,,,,,,,,",
            "Material / Apresenta\u00e7\u00e3o,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
            f",{description} / 500MG (100.1),,,,,COMPR,,,GRUPO TESTE (47),,,,,L001 / 28/02/2028,{quantity},,,,,",
        ]
        rows.extend(extra_rows or [])
        csv_text = "\n".join(rows)
        return SimpleUploadedFile(
            name,
            csv_text.encode("utf-8"),
            content_type="text/csv",
        )

    def post_csv(self, upload=None):
        return self.client.post(
            self.url,
            {"arquivo": upload or self.csv_upload()},
            format="multipart",
        )

    def assert_domain_is_empty(self):
        self.assertEqual(Importacao.objects.count(), 0)
        self.assertEqual(Competencia.objects.count(), 0)
        self.assertEqual(Ups.objects.count(), 0)
        self.assertEqual(SubgrupoGmus.objects.count(), 0)
        self.assertEqual(Medicamento.objects.count(), 0)
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(Estoque.objects.count(), 0)

    def test_unauthenticated_user_cannot_upload_inventory(self):
        response = self.post_csv()

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assert_domain_is_empty()

    def test_upload_requires_a_file(self):
        self.authenticate()

        response = self.client.post(self.url, {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("arquivo", response.data)
        self.assert_domain_is_empty()

    def test_upload_rejects_non_csv_extension_before_parsing(self):
        self.authenticate()

        with patch("importacoes.views.parse_inventory_csv") as parser:
            response = self.post_csv(self.csv_upload(name="inventario.txt"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        parser.assert_not_called()
        self.assert_domain_is_empty()

    def test_valid_upload_persists_inventory(self):
        self.authenticate()

        response = self.post_csv()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Importacao.objects.get().nome_arquivo, "inventario-ficticio.csv")
        self.assertEqual(Medicamento.objects.count(), 1)
        self.assertEqual(Lote.objects.count(), 1)
        self.assertEqual(Estoque.objects.count(), 1)
        self.assertEqual(Importacao.objects.get().status, Importacao.Status.CONCLUIDA)

    def test_upload_with_rejected_record_is_completed_partially(self):
        self.authenticate()
        upload = self.csv_upload(
            extra_rows=[",,,,,,,,,,,,,,L002 / 31/03/2028,-1,,,,,"]
        )

        response = self.post_csv(upload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "concluida_parcial")
        self.assertEqual(response.data["estoques_criados"], 1)
        self.assertEqual(response.data["registros_ignorados"], 1)
        self.assertEqual(Estoque.objects.count(), 1)
        self.assertEqual(response.data["erros"][0]["type"], "negative_quantity")

    def test_duplicate_inventory_returns_conflict_without_new_stock(self):
        self.authenticate()
        first_response = self.post_csv()

        second_response = self.post_csv()

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Ja existe uma importacao", second_response.data["erro"])
        self.assertEqual(Importacao.objects.count(), 1)
        self.assertEqual(Estoque.objects.count(), 1)

    def test_parser_exception_returns_bad_request(self):
        self.authenticate()

        with patch(
            "importacoes.views.parse_inventory_csv",
            side_effect=ValueError("data de validade invalida"),
        ):
            response = self.post_csv()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("Traceback", str(response.data))
        self.assert_domain_is_empty()

    def test_global_parser_error_blocks_persistence(self):
        self.authenticate()
        parsed_data = {
            "records": [],
            "inconsistencies": [
                {
                    "type": "invalid_report",
                    "severity": "error",
                    "message": "Estrutura global invalida.",
                }
            ],
        }

        with patch("importacoes.views.parse_inventory_csv", return_value=parsed_data), patch(
            "importacoes.views.persist_inventory_import"
        ) as persistence:
            response = self.post_csv()

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        persistence.assert_not_called()
        self.assert_domain_is_empty()

    def test_unexpected_persistence_error_rolls_back_everything(self):
        self.authenticate()

        with self.assertLogs("importacoes.views", level="ERROR"), patch(
            "importacoes.services.Estoque.objects.create",
            side_effect=RuntimeError("falha inesperada simulada"),
        ):
            response = self.post_csv()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.data,
            {"erro": "Ocorreu um erro inesperado ao processar a importacao."},
        )
        self.assert_domain_is_empty()

    def test_success_response_contains_summary_and_relevant_warnings(self):
        self.authenticate()
        Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="DESCRICAO JA CADASTRADA",
            unidade="FRASC",
        )

        response = self.post_csv()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "concluida_com_alertas")
        self.assertEqual(response.data["tipo_relatorio"], "inventario")
        self.assertEqual(response.data["competencia"], {"ano": 2026, "mes": 8})
        self.assertEqual(response.data["ups"]["codigo_gmus"], "1234567")
        self.assertEqual(response.data["registros_processados"], 1)
        self.assertEqual(response.data["registros_ignorados"], 0)
        self.assertEqual(response.data["medicamentos_criados"], 0)
        self.assertEqual(response.data["medicamentos_reutilizados"], 1)
        self.assertEqual(response.data["lotes_criados"], 1)
        self.assertEqual(response.data["lotes_reutilizados"], 0)
        self.assertEqual(response.data["estoques_criados"], 1)
        self.assertEqual(len(response.data["divergencias"]), 3)
        self.assertEqual(response.data["warnings"], [])
        self.assertEqual(response.data["erros"], [])
        self.assertNotIn("raw", str(response.data))
