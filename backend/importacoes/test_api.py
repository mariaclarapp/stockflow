import unittest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote, SaldoEstoque
from medicamentos.models import Medicamento, SubgrupoGmus

from .models import Importacao, ImportacaoExclusao, PendenciaImportacao


@unittest.skip("Fluxo HTTP legado de inventario removido do escopo ativo.")
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
            ",,Inventário,,,,,,,,,,,,,,,,,,",
            "Filtros: Compet\u00eancia: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Nao. Imp. Inativo? Nao. Ordenado por: Codigo.,,,,,,,,,,,,,,,,,,,,,",
            "Unidade: 9 - FARMACIA TESTE - PR,,,,,,,,,,,,,,,,,,,,",
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

    def post_csv(self, upload=None, *, reimportar=None):
        data = {"arquivo": upload if upload is not None else self.csv_upload()}
        if reimportar is not None:
            data["reimportar"] = reimportar
        return self.client.post(
            self.url,
            data,
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

        with patch("importacoes.views.parse_report_csv") as parser:
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
        self.assertFalse(response.data["reimportacao"])

    def test_unknown_report_returns_controlled_error_without_persistence(self):
        self.authenticate()
        upload = SimpleUploadedFile(
            "relatorio.csv",
            b"codigo,descricao\n1,ARQUIVO GENERICO",
            content_type="text/csv",
        )

        response = self.post_csv(upload)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data, {"erro": "Tipo de relatório não reconhecido."})
        self.assert_domain_is_empty()

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

    def test_explicit_reimport_updates_same_import_and_returns_ok(self):
        self.authenticate()
        first_response = self.post_csv()
        importacao = Importacao.objects.get()
        original_pk = importacao.pk
        original_hash = importacao.hash_arquivo
        original_stock_ids = list(importacao.estoques.values_list("pk", flat=True))

        response = self.post_csv(
            self.csv_upload(
                name="inventario-corrigido.csv",
                quantity="25",
            ),
            reimportar=True,
        )

        importacao.refresh_from_db()
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["reimportacao"])
        self.assertEqual(response.data["importacao_id"], original_pk)
        self.assertEqual(importacao.pk, original_pk)
        self.assertEqual(importacao.nome_arquivo, "inventario-corrigido.csv")
        self.assertNotEqual(importacao.hash_arquivo, original_hash)
        self.assertFalse(Estoque.objects.filter(pk__in=original_stock_ids).exists())
        self.assertEqual(importacao.estoques.get().quantidade, 25)

    def test_reimport_with_same_hash_returns_conflict_without_replacement(self):
        self.authenticate()
        self.post_csv()
        importacao = Importacao.objects.get()
        original_stock_ids = list(importacao.estoques.values_list("pk", flat=True))

        response = self.post_csv(reimportar=True)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("mesmo arquivo", response.data["erro"])
        self.assertEqual(
            list(importacao.estoques.values_list("pk", flat=True)),
            original_stock_ids,
        )

    def test_unknown_report_during_reimport_preserves_old_inventory(self):
        self.authenticate()
        self.post_csv()
        importacao = Importacao.objects.get()
        original_stock_ids = list(importacao.estoques.values_list("pk", flat=True))
        unknown = SimpleUploadedFile(
            "desconhecido.csv",
            b"codigo,descricao\n1,RELATORIO DESCONHECIDO",
            content_type="text/csv",
        )

        response = self.post_csv(unknown, reimportar=True)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(Importacao.objects.count(), 1)
        self.assertEqual(
            list(importacao.estoques.values_list("pk", flat=True)),
            original_stock_ids,
        )

    def test_parser_failure_during_reimport_preserves_old_inventory(self):
        self.authenticate()
        self.post_csv()
        importacao = Importacao.objects.get()
        original_stock_ids = list(importacao.estoques.values_list("pk", flat=True))

        with patch(
            "importacoes.views.parse_report_csv",
            side_effect=ValueError("falha de parsing"),
        ):
            response = self.post_csv(
                self.csv_upload(quantity="30"),
                reimportar=True,
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Importacao.objects.count(), 1)
        self.assertEqual(
            list(importacao.estoques.values_list("pk", flat=True)),
            original_stock_ids,
        )

    def test_parser_exception_returns_bad_request(self):
        self.authenticate()

        with patch(
            "importacoes.views.parse_report_csv",
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

        with patch("importacoes.views.parse_report_csv", return_value=parsed_data), patch(
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
        self.assertEqual(response.data["ups"]["id_unidade_gmus"], "9")
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


def stock_upload(name="estoque.csv"):
    content = "\n".join(
        [
            "RIBEIRAO CLARO - PR,,,,",
            "Consulta de Estoque,,,,",
            "Filtros: Competência Inicial: 202608 Competência Final: 202608 UPS: FARMACIA TESTE / 1234567 (9) Estoque Zerado: Ambos Produtos Inativos: Não,,,,",
            ",Unidade: FARMACIA TESTE (9),,,",
            ",,Material / Apresentação,,,,,,,,,Unidade,Quantidade,,Conferência,",
            ",,DIPIRONA - 500MG (115.1),,,,,,,,,COMPR,1.234,,,",
        ]
    )
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


def stock_upload_with_missing_code(name="estoque-sem-codigo.csv"):
    content = "\n".join(
        [
            "RIBEIRAO CLARO - PR,,,,",
            "Consulta de Estoque,,,,",
            "Filtros: Competência Inicial: 202608 Competência Final: 202608 UPS: FARMACIA TESTE / 1234567 (9) Estoque Zerado: Ambos Produtos Inativos: Não,,,,",
            ",Unidade: FARMACIA TESTE (9),,,",
            ",,Material / Apresentação,,,,,,,,,Unidade,Quantidade,,Conferência,",
            ",,DIPIRONA - 500MG (115.1),,,,,,,,,COMPR,1.234,,,,",
            ",,CIANOCOBALAMINA+PIRIDOXINA+TIAMINA+DEXAMETASONA - 5MG+100MG,,,,,,,,,AMPOL,41,,,,",
        ]
    )
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


def stock_upload_without_ups_code(name="estoque-sem-codigo-ups.csv"):
    content = "\n".join(
        [
            "RIBEIRAO CLARO - PR,,,,",
            "Consulta de Estoque,,,,",
            "Filtros: Competência Inicial: 202608 Competência Final: 202608 UPS: FARMACIA TESTE (9) Estoque Zerado: Ambos Produtos Inativos: Não,,,,",
            ",Unidade: FARMACIA TESTE (9),,,",
            ",,Material / Apresentação,,,,,,,,,Unidade,Quantidade,,Conferência,",
            ",,DIPIRONA - 500MG (115.1),,,,,,,,,COMPR,1.234,,,,",
        ]
    )
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


class ActiveImportApiTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="staff-importacao-ativa",
            password="senha-ficticia",
            is_staff=True,
        )
        self.stock_url = reverse("stock-import-upload")
        self.preview_url = reverse("importacao-preview")

    def authenticate(self):
        self.client.force_authenticate(self.staff)

    def test_preview_is_read_only(self):
        self.authenticate()
        response = self.client.post(
            self.preview_url,
            {"arquivo": stock_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tipo_relatorio"], "estoque")
        self.assertEqual(response.data["registros_identificados"], 1)
        self.assertTrue(response.data["pode_importar"])
        self.assertFalse(Importacao.objects.exists())

    def test_stock_upload_resolves_ups_when_report_omits_gmus_code(self):
        self.authenticate()
        ups = Ups.objects.create(
            codigo_gmus="1234567",
            id_unidade_gmus="9",
            nome="FARMACIA TESTE",
        )

        response = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_without_ups_code()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Importacao.objects.get().ups, ups)
        self.assertEqual(response.data["registros_processados"], 1)

    def test_import_and_audited_delete_require_confirmation(self):
        self.authenticate()
        upload = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload()},
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        importacao = Importacao.objects.get()
        delete_url = reverse("importacao-delete", args=[importacao.pk])

        refused = self.client.delete(delete_url, {}, format="json")
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Importacao.objects.filter(pk=importacao.pk).exists())

        deleted = self.client.delete(
            delete_url,
            {"confirmar": True},
            format="json",
        )
        self.assertEqual(deleted.status_code, status.HTTP_200_OK)
        self.assertFalse(Importacao.objects.filter(pk=importacao.pk).exists())
        self.assertTrue(Competencia.objects.filter(pk=importacao.competencia_id).exists())
        competencias = self.client.get(reverse("competencia-list"))
        self.assertEqual(competencias.status_code, status.HTTP_200_OK)
        self.assertEqual(competencias.data, [])
        audit = ImportacaoExclusao.objects.get()
        self.assertEqual(audit.importacao_id_original, importacao.pk)
        self.assertEqual(audit.excluida_por, self.staff)
        self.assertEqual(audit.contagens["saldos_excluidos"], 1)

    def test_missing_code_creates_resolvable_pending_and_resolution_applies_stock(self):
        self.authenticate()
        upload = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_with_missing_code()},
            format="multipart",
        )

        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        self.assertEqual(upload.data["status"], Importacao.Status.CONCLUIDA_PARCIAL)
        self.assertEqual(upload.data["quantidade_nao_associada"], 41)
        self.assertEqual(len(upload.data["pendencias"]), 1)
        pendencia = PendenciaImportacao.objects.get()
        self.assertEqual(pendencia.quantidade, 41)

        resolve = self.client.post(
            reverse(
                "importacao-pendencia-resolver",
                args=[pendencia.importacao_id, pendencia.pk],
            ),
            {"codigo_gmus": "184.1"},
            format="json",
        )

        self.assertEqual(resolve.status_code, status.HTTP_200_OK)
        self.assertTrue(resolve.data["medicamento_criado"])
        self.assertTrue(resolve.data["saldo_criado"])
        self.assertEqual(
            resolve.data["importacao"]["status"],
            Importacao.Status.CONCLUIDA,
        )
        self.assertEqual(resolve.data["importacao"]["quantidade_nao_associada"], "0.000")
        self.assertEqual(resolve.data["importacao"]["pendencias"], [])
        saldo = SaldoEstoque.objects.get(medicamento__codigo_gmus="184.1")
        self.assertEqual(saldo.quantidade, 41)
        pendencia.refresh_from_db()
        self.assertEqual(pendencia.status, PendenciaImportacao.Status.RESOLVIDA)
        self.assertEqual(pendencia.resolvida_por, self.staff)

    def test_resolution_rejects_invalid_generic_code(self):
        self.authenticate()
        self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_with_missing_code()},
            format="multipart",
        )
        pendencia = PendenciaImportacao.objects.get()

        response = self.client.post(
            reverse(
                "importacao-pendencia-resolver",
                args=[pendencia.importacao_id, pendencia.pk],
            ),
            {"codigo_gmus": "SEM-CODIGO"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PendenciaImportacao.objects.filter(pk=pendencia.pk, status="pendente").exists())
        self.assertFalse(Medicamento.objects.filter(codigo_gmus="SEM-CODIGO").exists())

    def test_explicit_reimport_can_reprocess_the_same_file_to_create_pending(self):
        self.authenticate()
        first = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_with_missing_code()},
            format="multipart",
        )
        importacao_id = first.data["importacao_id"]

        second = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_with_missing_code(), "reimportar": True},
            format="multipart",
        )

        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["importacao_id"], importacao_id)
        self.assertEqual(PendenciaImportacao.objects.count(), 1)

    def test_unique_missing_code_match_is_internal_info_not_visible_warning(self):
        self.authenticate()
        Medicamento.objects.create(
            codigo_gmus="184.1",
            descricao="CIANOCOBALAMINA+PIRIDOXINA+TIAMINA+DEXAMETASONA - 5MG+100MG",
            unidade="AMPOL",
        )

        response = self.client.post(
            self.stock_url,
            {"arquivo": stock_upload_with_missing_code()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Importacao.Status.CONCLUIDA)
        self.assertEqual(response.data["warnings"], [])
        self.assertEqual(response.data["erros"], [])
        self.assertEqual(response.data["pendencias"], [])
        self.assertEqual(
            SaldoEstoque.objects.get(medicamento__codigo_gmus="184.1").quantidade,
            41,
        )
