import hashlib
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Competencia, Ups
from estoques.models import Estoque, Lote
from medicamentos.domain import CLASSIFICACAO_MANIPULADO
from medicamentos.models import Classificacao, Medicamento, SubgrupoGmus

from .models import Importacao
from .parsers import parse_inventory_csv
from .services import (
    DuplicateInventoryImportError,
    ReimportationTargetNotFoundError,
    SameInventoryFileError,
    persist_inventory_import,
)


class InventoryPersistenceServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="farmaceutica_teste",
            password="senha-ficticia",
        )
        self.file_hash = hashlib.sha256(b"arquivo-ficticio").hexdigest()

    def parsed_data(self, records=None, inconsistencies=None):
        return {
            "tipo_relatorio": "inventario",
            "hash_arquivo": self.file_hash,
            "metadata": {
                "competencia": {"raw": "202608", "ano": 2026, "mes": 8},
                "ups": {
                    "nome": "FARMACIA TESTE",
                    "codigo_gmus": "1234567",
                    "id_unidade_gmus": "9",
                },
            },
            "records": records if records is not None else [self.record()],
            "inconsistencies": inconsistencies or [],
        }

    def record(
        self,
        *,
        line=1,
        code="100.1",
        description="MEDICAMENTO TESTE / 500MG",
        unit="COMPR",
        subgroup=None,
        lot_code="L001",
        validity=date(2028, 2, 28),
        quantity=Decimal("10"),
    ):
        lot = None
        if lot_code is not None:
            lot = {"codigo_lote": lot_code, "validade": validity}
        return {
            "line": line,
            "medicamento": {
                "codigo_gmus": code,
                "descricao": description,
                "descricao_original": f"{description} ({code})",
                "unidade": unit,
                "subgrupo": subgroup,
            },
            "lote": lot,
            "quantidade": quantity,
            "raw": {},
        }

    def persist(
        self,
        parsed_data=None,
        *,
        reimportar=False,
        nome_arquivo="inventario-ficticio.csv",
        user=None,
    ):
        return persist_inventory_import(
            parsed_data=parsed_data or self.parsed_data(),
            user=user or self.user,
            nome_arquivo=nome_arquivo,
            reimportar=reimportar,
        )

    def test_persists_valid_inventory_with_one_medicine(self):
        summary = self.persist()

        stock = Estoque.objects.select_related(
            "medicamento", "ups", "competencia", "importacao"
        ).get()
        self.assertTrue(summary["importacao_criada"])
        self.assertEqual(summary["registros_processados"], 1)
        self.assertEqual(summary["medicamentos_criados"], 1)
        self.assertEqual(summary["lotes_criados"], 1)
        self.assertEqual(summary["estoques_criados"], 1)
        self.assertEqual(stock.medicamento.codigo_gmus, "100.1")
        self.assertEqual(stock.medicamento.descricao, "MEDICAMENTO TESTE / 500MG")
        self.assertEqual(stock.medicamento.unidade, "COMPR")
        self.assertEqual(stock.ups.codigo_gmus, "1234567")
        self.assertEqual(stock.ups.id_unidade_gmus, "9")
        self.assertEqual(stock.competencia.ano, 2026)
        self.assertEqual(stock.importacao.usuario, self.user)
        self.assertEqual(stock.importacao.tipo_relatorio, "inventario")
        self.assertEqual(stock.importacao.hash_arquivo, self.file_hash)
        self.assertEqual(stock.importacao.status, Importacao.Status.CONCLUIDA)

    def test_persists_multiple_lots_for_same_medicine(self):
        parsed_data = self.parsed_data(
            records=[
                self.record(line=1, lot_code="L001"),
                self.record(line=2, lot_code="L002", quantity=Decimal("20")),
            ]
        )

        summary = self.persist(parsed_data)

        self.assertEqual(Medicamento.objects.count(), 1)
        self.assertEqual(Lote.objects.count(), 2)
        self.assertEqual(Estoque.objects.count(), 2)
        self.assertEqual(summary["medicamentos_criados"], 1)
        self.assertEqual(summary["lotes_criados"], 2)

    def test_reuses_existing_medicine(self):
        existing = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE / 500MG",
            unidade="COMPR",
        )

        summary = self.persist()

        self.assertEqual(Medicamento.objects.count(), 1)
        self.assertEqual(Estoque.objects.get().medicamento, existing)
        self.assertEqual(summary["medicamentos_reutilizados"], 1)

    def test_new_manipulated_medicine_receives_classification(self):
        self.persist(
            self.parsed_data(
                records=[
                    self.record(
                        description="MEDICAMENTO (manipulado) / 30MG",
                    )
                ]
            )
        )

        medicine = Medicamento.objects.get()
        classification = Classificacao.objects.get(
            nome=CLASSIFICACAO_MANIPULADO
        )
        self.assertTrue(classification.ativo)
        self.assertTrue(medicine.classificacoes.filter(pk=classification.pk).exists())

    def test_existing_medicine_receives_manipulated_classification(self):
        medicine = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO (MANIPULADO) / 30MG",
            unidade="CAPS",
        )

        self.persist(
            self.parsed_data(
                records=[
                    self.record(
                        description="MEDICAMENTO (MANIPULADO) / 30MG",
                        unit="CAPS",
                    )
                ]
            )
        )

        self.assertTrue(
            medicine.classificacoes.filter(
                nome=CLASSIFICACAO_MANIPULADO,
                ativo=True,
            ).exists()
        )

    def test_manipulated_association_is_not_duplicated_for_multiple_lots(self):
        records = [
            self.record(
                line=1,
                description="MEDICAMENTO (MANIPULADO) / 30MG",
                lot_code="L001",
            ),
            self.record(
                line=2,
                description="MEDICAMENTO (MANIPULADO) / 30MG",
                lot_code="L002",
            ),
        ]

        self.persist(self.parsed_data(records=records))

        medicine = Medicamento.objects.get()
        self.assertEqual(
            medicine.classificacoes.filter(nome=CLASSIFICACAO_MANIPULADO).count(),
            1,
        )

    def test_common_medicine_does_not_receive_manipulated_classification(self):
        self.persist()

        self.assertFalse(Classificacao.objects.exists())
        self.assertEqual(Medicamento.objects.get().classificacoes.count(), 0)

    def test_manipulated_classification_is_reused_and_reactivated(self):
        classification = Classificacao.objects.create(
            nome=CLASSIFICACAO_MANIPULADO,
            ativo=False,
        )
        records = [
            self.record(
                line=1,
                code="100.1",
                description="MEDICAMENTO A (MANIPULADO) / 30MG",
            ),
            self.record(
                line=2,
                code="101.1",
                description="MEDICAMENTO B (MANIPULADO) / 60MG",
                lot_code="L002",
            ),
        ]

        self.persist(self.parsed_data(records=records))

        classification.refresh_from_db()
        self.assertTrue(classification.ativo)
        self.assertEqual(Classificacao.objects.count(), 1)
        self.assertEqual(classification.medicamentos.count(), 2)

    def test_reuses_existing_competence_and_ups(self):
        competence = Competencia.objects.create(ano=2026, mes=8)
        ups = Ups.objects.create(
            codigo_gmus="1234567",
            id_unidade_gmus="9",
            nome="FARMACIA TESTE",
        )

        summary = self.persist()

        stock = Estoque.objects.get()
        self.assertEqual(stock.competencia, competence)
        self.assertEqual(stock.ups, ups)
        self.assertFalse(summary["competencia_criada"])
        self.assertFalse(summary["ups_criada"])

    def test_uses_report_type_returned_by_parser(self):
        parsed_data = self.parsed_data()
        parsed_data["tipo_relatorio"] = "inventario_teste"

        self.persist(parsed_data)

        self.assertEqual(Importacao.objects.get().tipo_relatorio, "inventario_teste")

    def test_optional_subgroup_and_lot_do_not_create_related_records(self):
        summary = self.persist(
            self.parsed_data(records=[self.record(subgroup=None, lot_code=None)])
        )

        medicine = Medicamento.objects.get()
        stock = Estoque.objects.get()
        self.assertIsNone(medicine.subgrupo_gmus)
        self.assertIsNone(stock.lote)
        self.assertEqual(SubgrupoGmus.objects.count(), 0)
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(summary["lotes_criados"], 0)

    def test_creates_subgroup_when_report_informs_it(self):
        subgroup = {"codigo_gmus": "47", "nome": "GRUPO TESTE"}

        self.persist(self.parsed_data(records=[self.record(subgroup=subgroup)]))

        medicine = Medicamento.objects.select_related("subgrupo_gmus").get()
        self.assertEqual(medicine.subgrupo_gmus.codigo_gmus, 47)
        self.assertEqual(medicine.subgrupo_gmus.nome, "GRUPO TESTE")

    def test_reuses_lot_by_medicine_lot_code_and_validity(self):
        medicine = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE / 500MG",
            unidade="COMPR",
        )
        lot = Lote.objects.create(
            medicamento=medicine,
            codigo_lote="L001",
            data_validade=date(2028, 2, 28),
        )

        summary = self.persist()

        self.assertEqual(Lote.objects.count(), 1)
        self.assertEqual(Estoque.objects.get().lote, lot)
        self.assertEqual(summary["lotes_reutilizados"], 1)

    def test_does_not_choose_between_ambiguous_matching_lots(self):
        medicine = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="MEDICAMENTO TESTE / 500MG",
            unidade="COMPR",
        )
        for _ in range(2):
            Lote.objects.create(
                medicamento=medicine,
                codigo_lote="L001",
                data_validade=date(2028, 2, 28),
            )

        summary = self.persist()

        self.assertEqual(Estoque.objects.count(), 0)
        self.assertEqual(summary["registros_ignorados"], 1)
        self.assertIn(
            "mais de uma correspondencia",
            summary["erros"][0]["message"],
        )
        self.assertEqual(
            summary["importacao"].status,
            Importacao.Status.CONCLUIDA_PARCIAL,
        )

    def test_rolls_back_entire_import_on_unexpected_persistence_error(self):
        with patch(
            "importacoes.services.Estoque.objects.create",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                self.persist()

        self.assertEqual(Importacao.objects.count(), 0)
        self.assertEqual(Competencia.objects.count(), 0)
        self.assertEqual(Ups.objects.count(), 0)
        self.assertEqual(SubgrupoGmus.objects.count(), 0)
        self.assertEqual(Medicamento.objects.count(), 0)
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(Estoque.objects.count(), 0)

    def test_uses_only_virtual_quantity_and_does_not_persist_real_quantity(self):
        stock_row = [""] * 21
        stock_row[1] = "MEDICAMENTO TESTE / 500MG (100.1)"
        stock_row[6] = "COMPR"
        stock_row[14] = "L001 / 28/02/2028"
        stock_row[15] = "1.234"
        stock_row[18] = "VALOR IGNORADO"
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",".join(stock_row),
            ]
        )
        parsed_data = parse_inventory_csv(csv_text.encode("utf-8"))

        self.persist(parsed_data)

        self.assertEqual(Estoque.objects.get().quantidade, Decimal("1234"))
        self.assertNotIn("quantidade_real", parsed_data["records"][0])
        self.assertFalse(hasattr(Estoque, "quantidade_real"))

    def test_existing_medicine_divergence_is_returned_without_overwrite(self):
        medicine = Medicamento.objects.create(
            codigo_gmus="100.1",
            descricao="DESCRICAO CADASTRADA",
            unidade="FRASC",
        )

        summary = self.persist()

        medicine.refresh_from_db()
        self.assertEqual(medicine.descricao, "DESCRICAO CADASTRADA")
        self.assertEqual(medicine.unidade, "FRASC")
        self.assertEqual(
            {item["tipo"] for item in summary["divergencias"]},
            {"medicamento_descricao", "medicamento_unidade"},
        )
        self.assertEqual(
            summary["importacao"].status,
            Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )

    def test_does_not_persist_record_marked_inconsistent_by_parser(self):
        parsed_data = self.parsed_data(
            records=[self.record(line=10), self.record(line=11, code="101.1")],
            inconsistencies=[
                {
                    "line": 10,
                    "type": "invalid_quantity",
                    "severity": "error",
                    "message": "Qtde Virt. invalida.",
                }
            ],
        )

        summary = self.persist(parsed_data)

        self.assertEqual(Estoque.objects.count(), 1)
        self.assertEqual(Estoque.objects.get().medicamento.codigo_gmus, "101.1")
        self.assertEqual(summary["registros_ignorados"], 1)
        self.assertEqual(len(summary["erros"]), 1)
        self.assertEqual(
            summary["importacao"].status,
            Importacao.Status.CONCLUIDA_PARCIAL,
        )

    def test_negative_quantity_is_rejected_by_persistence(self):
        parsed_data = self.parsed_data(
            records=[
                self.record(line=10, quantity=Decimal("-1")),
                self.record(line=11, code="101.1"),
            ]
        )

        summary = self.persist(parsed_data)

        self.assertEqual(Estoque.objects.count(), 1)
        self.assertEqual(Estoque.objects.get().medicamento.codigo_gmus, "101.1")
        self.assertEqual(summary["registros_ignorados"], 1)
        self.assertEqual(summary["erros"][0]["type"], "persistence_validation")
        self.assertEqual(
            summary["importacao"].status,
            Importacao.Status.CONCLUIDA_PARCIAL,
        )

    def test_warning_sets_alert_status_without_rejecting_record(self):
        parsed_data = self.parsed_data(
            inconsistencies=[
                {
                    "line": 1,
                    "type": "example_warning",
                    "severity": "warning",
                    "message": "Aviso ficticio.",
                }
            ]
        )

        summary = self.persist(parsed_data)

        self.assertEqual(Estoque.objects.count(), 1)
        self.assertEqual(summary["registros_ignorados"], 0)
        self.assertEqual(
            summary["importacao"].status,
            Importacao.Status.CONCLUIDA_COM_ALERTAS,
        )

    def test_blocks_duplicate_import_for_competence_ups_and_report_type(self):
        self.persist()

        with self.assertRaisesRegex(
            DuplicateInventoryImportError,
            "Ja existe uma importacao",
        ):
            self.persist()

        self.assertEqual(Importacao.objects.count(), 1)
        self.assertEqual(Estoque.objects.count(), 1)

    def test_explicit_reimport_reuses_import_and_replaces_stocks_and_metadata(self):
        original_data = self.parsed_data(
            records=[
                self.record(line=1, code="100.1", quantity=Decimal("10")),
                self.record(line=2, code="101.1", lot_code="L002"),
            ]
        )
        original = self.persist(original_data)["importacao"]
        original_pk = original.pk
        original_stock_ids = set(original.estoques.values_list("pk", flat=True))
        shared_medicine = Medicamento.objects.get(codigo_gmus="101.1")
        replacement_user = get_user_model().objects.create_user(
            username="farmaceutica_reimportacao",
            password="senha-ficticia",
        )
        replacement_data = self.parsed_data(
            records=[self.record(code="100.1", quantity=Decimal("25"))]
        )
        replacement_data["hash_arquivo"] = hashlib.sha256(
            b"arquivo-substituto"
        ).hexdigest()

        summary = self.persist(
            replacement_data,
            reimportar=True,
            nome_arquivo="inventario-corrigido.csv",
            user=replacement_user,
        )

        original.refresh_from_db()
        self.assertTrue(summary["reimportacao"])
        self.assertFalse(summary["importacao_criada"])
        self.assertEqual(original.pk, original_pk)
        self.assertEqual(original.nome_arquivo, "inventario-corrigido.csv")
        self.assertEqual(original.hash_arquivo, replacement_data["hash_arquivo"])
        self.assertEqual(original.usuario, replacement_user)
        self.assertFalse(Estoque.objects.filter(pk__in=original_stock_ids).exists())
        self.assertEqual(original.estoques.count(), 1)
        self.assertEqual(original.estoques.get().quantidade, Decimal("25"))
        self.assertTrue(Medicamento.objects.filter(pk=shared_medicine.pk).exists())

    def test_reimport_does_not_change_other_ups_or_competence_stocks(self):
        primary = self.persist()["importacao"]
        other_ups_data = self.parsed_data(
            records=[self.record(code="200.1", lot_code="UPS-2")]
        )
        other_ups_data["metadata"]["ups"] = {
            "nome": "OUTRA UPS",
            "codigo_gmus": "1234567",
            "id_unidade_gmus": "10",
        }
        other_ups = self.persist(other_ups_data)["importacao"]
        other_competence_data = self.parsed_data(
            records=[self.record(code="300.1", lot_code="COMP-2")]
        )
        other_competence_data["metadata"]["competencia"] = {
            "raw": "202609",
            "ano": 2026,
            "mes": 9,
        }
        other_competence = self.persist(other_competence_data)["importacao"]
        protected_stock_ids = set(
            Estoque.objects.filter(
                importacao__in=[other_ups, other_competence]
            ).values_list("pk", flat=True)
        )
        replacement = self.parsed_data(
            records=[self.record(quantity=Decimal("99"))]
        )
        replacement["hash_arquivo"] = hashlib.sha256(b"replacement").hexdigest()

        self.persist(replacement, reimportar=True)

        self.assertEqual(primary.estoques.count(), 1)
        self.assertEqual(
            set(Estoque.objects.filter(pk__in=protected_stock_ids).values_list("pk", flat=True)),
            protected_stock_ids,
        )

    def test_same_hash_does_not_replace_existing_inventory(self):
        importacao = self.persist()["importacao"]
        original_stock_ids = list(importacao.estoques.values_list("pk", flat=True))

        with self.assertRaisesRegex(SameInventoryFileError, "mesmo arquivo"):
            self.persist(reimportar=True)

        importacao.refresh_from_db()
        self.assertEqual(importacao.hash_arquivo, self.file_hash)
        self.assertEqual(
            list(importacao.estoques.values_list("pk", flat=True)),
            original_stock_ids,
        )

    def test_reimport_requires_target_for_detected_competence_and_ups(self):
        with self.assertRaisesRegex(
            ReimportationTargetNotFoundError,
            "Nao existe importacao",
        ):
            self.persist(reimportar=True)

        self.assertEqual(Importacao.objects.count(), 0)
        self.assertEqual(Competencia.objects.count(), 0)
        self.assertEqual(Ups.objects.count(), 0)
        self.assertEqual(Medicamento.objects.count(), 0)
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(Estoque.objects.count(), 0)

    def test_reimport_keeps_manipulated_classification_behavior(self):
        importacao = self.persist()["importacao"]
        replacement = self.parsed_data(
            records=[
                self.record(description="MEDICAMENTO (MANIPULADO) / 500MG")
            ]
        )
        replacement["hash_arquivo"] = hashlib.sha256(b"manipulado").hexdigest()

        self.persist(replacement, reimportar=True)

        medicine = importacao.estoques.get().medicamento
        self.assertTrue(
            medicine.classificacoes.filter(
                nome=CLASSIFICACAO_MANIPULADO,
                ativo=True,
            ).exists()
        )

    def test_reimport_rolls_back_old_stocks_after_partial_new_persistence(self):
        original_data = self.parsed_data(
            records=[
                self.record(line=1, code="100.1", quantity=Decimal("10")),
                self.record(line=2, code="101.1", lot_code="L002", quantity=Decimal("20")),
            ]
        )
        importacao = self.persist(original_data)["importacao"]
        original_import = {
            "nome_arquivo": importacao.nome_arquivo,
            "hash_arquivo": importacao.hash_arquivo,
            "status": importacao.status,
            "usuario_id": importacao.usuario_id,
        }
        original_stocks = list(
            importacao.estoques.order_by("pk").values(
                "id",
                "medicamento_id",
                "lote_id",
                "quantidade",
            )
        )
        replacement = self.parsed_data(
            records=[
                self.record(line=1, code="200.1", lot_code="NEW-1"),
                self.record(line=2, code="201.1", lot_code="NEW-2"),
            ]
        )
        replacement["hash_arquivo"] = hashlib.sha256(b"falha-parcial").hexdigest()
        original_create = Estoque.objects.create
        create_calls = 0

        def fail_after_first_stock(**kwargs):
            nonlocal create_calls
            create_calls += 1
            if create_calls == 2:
                raise RuntimeError("falha depois do primeiro estoque novo")
            return original_create(**kwargs)

        with patch(
            "importacoes.services.Estoque.objects.create",
            side_effect=fail_after_first_stock,
        ):
            with self.assertRaisesRegex(RuntimeError, "primeiro estoque novo"):
                self.persist(replacement, reimportar=True)

        importacao.refresh_from_db()
        self.assertEqual(
            {
                "nome_arquivo": importacao.nome_arquivo,
                "hash_arquivo": importacao.hash_arquivo,
                "status": importacao.status,
                "usuario_id": importacao.usuario_id,
            },
            original_import,
        )
        self.assertEqual(
            list(
                importacao.estoques.order_by("pk").values(
                    "id",
                    "medicamento_id",
                    "lote_id",
                    "quantidade",
                )
            ),
            original_stocks,
        )
        self.assertFalse(Medicamento.objects.filter(codigo_gmus__in=["200.1", "201.1"]).exists())

    def test_distinguishes_ups_with_shared_code_by_unit_identifier(self):
        farmacia_data = self.parsed_data()
        farmacia_data["metadata"]["ups"] = {
            "nome": "FARMACIA MUNICIPAL",
            "codigo_gmus": "2780046",
            "id_unidade_gmus": "9",
        }
        caf_data = self.parsed_data(records=[self.record(line=2, code="101.1")])
        caf_data["metadata"]["ups"] = {
            "nome": "CAF",
            "codigo_gmus": "2780046",
            "id_unidade_gmus": "10",
        }

        farmacia = self.persist(farmacia_data)
        caf = self.persist(caf_data)

        self.assertNotEqual(farmacia["importacao"].ups_id, caf["importacao"].ups_id)
        self.assertEqual(Ups.objects.count(), 2)
        self.assertEqual(Importacao.objects.count(), 2)
        self.assertEqual(
            Estoque.objects.get(
                medicamento__codigo_gmus="100.1"
            ).ups.id_unidade_gmus,
            "9",
        )
        self.assertEqual(
            Estoque.objects.get(
                medicamento__codigo_gmus="101.1"
            ).ups.id_unidade_gmus,
            "10",
        )

        for parsed_data in (farmacia_data, caf_data):
            with self.assertRaises(DuplicateInventoryImportError):
                self.persist(parsed_data)
