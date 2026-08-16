import hashlib
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .parsers import parse_inventory_csv


class InventoryCsvParserTests(SimpleTestCase):
    def parse(self, text):
        return parse_inventory_csv(text.encode("utf-8"))

    def test_parse_inventory_metadata_and_stock_records(self):
        csv_text = "\n".join(
            [
                ",,,MUNICIPIO TESTE - PR,,,,,,,,,,,,,,,,,",
                ",,,Secretaria de Teste,,,,,,,,,,,,,,,,,",
                ",,Inventário,,,,,,,,,,,,,,,,,,",
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Unidade: 9 - FARMACIA TESTE - PR,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",MEDICAMENTO A / 500MG (100.1),,,,,COMPR,,,GRUPO TESTE (47),,,,,L001 / 28/02/2028,1.234,,,,,",
                ",,,,,,,,,,,,,,L002 / 30/03/2028,5,,,,,",
                ",MEDICAMENTO B / 10MG (101.1),,,,,FRASC,,,,,,,,B001 / 31/12/2027,20,,,,,",
                ",,,,,,,,,,,,,,,,,11/08/2026 15:11,,,",
                ",,,,Relatório emitido pelo sistema G-MUS v26.06.09,,,Usuário:,,,,USUARIO TESTE,,,,,,,,,",
                ",,,,,,,,,,,,,,,,,,Página: 1,,",
                ",,,,,© Inovadora Sistemas de Gestão Ltda.,,,Base:,,,,base_teste,,,,,,,,",
                "Total de Registros da UPS: 2,,,,,,,,,,,,,,,,,,,,",
                "Total de Registros: 2,,,,,,,,,,,,,,,,,,,,",
                "Registros impressos:,,,,,,3,,,,,,,,,,,,,,",
            ]
        )

        result = self.parse(csv_text)

        self.assertEqual(result["tipo_relatorio"], "inventario")
        self.assertEqual(
            result["hash_arquivo"],
            hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(result["metadata"]["encoding"], "utf-8")
        self.assertEqual(result["metadata"]["delimiter"], ",")
        self.assertEqual(result["metadata"]["campo_quantidade_estoque"], "Qtde Virt.")
        self.assertEqual(result["metadata"]["competencia"], {"raw": "202608", "ano": 2026, "mes": 8})
        self.assertEqual(
            result["metadata"]["ups"],
            {
                "nome": "FARMACIA TESTE - PR",
                "codigo_gmus": "1234567",
                "id_unidade": "9",
            },
        )
        self.assertEqual(result["metadata"]["unidade"]["nome"], "FARMACIA TESTE - PR")
        self.assertEqual(result["metadata"]["totais"]["registros_ups"], 2)
        self.assertEqual(result["metadata"]["totais"]["registros"], 2)
        self.assertEqual(result["metadata"]["totais"]["registros_impressos"], 3)
        self.assertEqual(len(result["records"]), 3)

        first = result["records"][0]
        self.assertEqual(first["medicamento"]["codigo_gmus"], "100.1")
        self.assertEqual(first["medicamento"]["descricao"], "MEDICAMENTO A / 500MG")
        self.assertEqual(first["medicamento"]["unidade"], "COMPR")
        self.assertEqual(
            first["medicamento"]["subgrupo"],
            {"nome": "GRUPO TESTE", "codigo_gmus": "47"},
        )
        self.assertEqual(first["lote"]["codigo_lote"], "L001")
        self.assertEqual(first["lote"]["validade"], date(2028, 2, 28))
        self.assertEqual(first["quantidade"], Decimal("1234"))
        self.assertNotIn("quantidade_real", first)
        self.assertNotIn("localizacao", first)

        second = result["records"][1]
        self.assertEqual(second["medicamento"]["codigo_gmus"], "100.1")
        self.assertEqual(second["lote"]["codigo_lote"], "L002")
        self.assertEqual(second["quantidade"], Decimal("5"))

        self.assertEqual(result["inconsistencies"], [])

    def test_real_quantity_is_ignored_even_when_invalid(self):
        stock_row = [""] * 21
        stock_row[1] = "MEDICAMENTO A / 500MG (100.1)"
        stock_row[6] = "COMPR"
        stock_row[14] = "L001 / 28/02/2028"
        stock_row[15] = "1.234"
        stock_row[18] = "VALOR INVALIDO"
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",".join(stock_row),
            ]
        )

        result = self.parse(csv_text)

        record = result["records"][0]
        self.assertEqual(record["quantidade"], Decimal("1234"))
        self.assertNotIn("quantidade_real", record)
        self.assertEqual(record["raw"]["quantidade_virtual"], "1.234")
        self.assertNotIn("quantidade_real", record["raw"])
        self.assertEqual(result["inconsistencies"], [])

    def test_real_quantity_is_not_promoted_when_virtual_quantity_is_missing(self):
        stock_row = [""] * 21
        stock_row[1] = "MEDICAMENTO A / 500MG (100.1)"
        stock_row[6] = "COMPR"
        stock_row[14] = "L001 / 28/02/2028"
        stock_row[18] = "1.200"
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",".join(stock_row),
            ]
        )

        result = self.parse(csv_text)

        self.assertEqual(result["records"], [])
        self.assertIn(
            "invalid_quantity",
            [item["type"] for item in result["inconsistencies"]],
        )
        self.assertTrue(
            all(item["severity"] == "error" for item in result["inconsistencies"])
        )

    def test_parse_shifted_last_page_columns(self):
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.",
                ",MEDICAMENTO DESLOCADO / 5MG (200.1),,,,,,COMPR,,,,,,,,LD1 / 30/11/2027,1.020,,,,",
                ",,,,,,,,,,,,,,,LD2 / 30/12/2027,64,,,,",
            ]
        )

        result = self.parse(csv_text)

        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["records"][0]["medicamento"]["unidade"], "COMPR")
        self.assertEqual(result["records"][0]["lote"]["codigo_lote"], "LD1")
        self.assertEqual(result["records"][0]["quantidade"], Decimal("1020"))
        self.assertEqual(result["records"][1]["lote"]["codigo_lote"], "LD2")
        self.assertEqual(result["records"][1]["quantidade"], Decimal("64"))

    def test_parse_material_code_split_across_page_break(self):
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",MEDICAMENTO COM CODIGO NA PAGINA SEGUINTE / 15MG ,,,,,COMPR,,,,,,,,SPLIT1 / 30/10/2027,500,,,,,",
                ",,,,,,,,,,,,,,,,,11/08/2026 15:11,,,",
                ",,,,,,,,,,,,,,,,,,Página: 1,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",(253.1),,,,,,,,,,,,,,,,,,,",
            ]
        )

        result = self.parse(csv_text)

        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["medicamento"]["codigo_gmus"], "253.1")
        self.assertEqual(
            record["medicamento"]["descricao"],
            "MEDICAMENTO COM CODIGO NA PAGINA SEGUINTE / 15MG",
        )
        self.assertEqual(record["lote"]["codigo_lote"], "SPLIT1")
        self.assertEqual(record["quantidade"], Decimal("500"))
        self.assertIn("material_linha_anterior", record["raw"]["material"])

    def test_orphan_lot_is_reported_as_inconsistency(self):
        csv_text = "\n".join(
            [
                "Filtros: Competência: 202608. UPS: FARMACIA TESTE - PR / 1234567 (9). Imp. Zero? Não. Imp. Inativo? Não. Ordenado por: Código.,,,,,,,,,,,,,,,,,,,,",
                "Material / Apresentação,,,,,,Unidade,,,,Sub-Grupo,,,Lote / Validade,,,Qtde Virt.,,,Qtde R.,",
                ",,,,,,,,,,,,,,ORFAO / 30/10/2027,10,,,,,",
            ]
        )

        result = self.parse(csv_text)

        self.assertEqual(result["records"], [])
        self.assertIn(
            "orphan_lot",
            [item["type"] for item in result["inconsistencies"]],
        )
        self.assertTrue(
            all(item["severity"] == "error" for item in result["inconsistencies"])
        )
