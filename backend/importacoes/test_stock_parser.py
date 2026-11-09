from decimal import Decimal
from unittest import TestCase

from .parsers import parse_report_csv
from .report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK


class StockReportParserTests(TestCase):
    def test_parses_stock_report_metadata_and_totals(self):
        source = "\n".join(
            [
                "RIBEIRAO CLARO - PR,,,,",
                "Consulta de Estoque,,,,",
                "Filtros: Competência Inicial: 202608 Competência Final: 202608 UPS: FARMACIA TESTE / 1234567 (9) Estoque Zerado: Ambos Produtos Inativos: Não,,,,",
                ",Unidade: FARMACIA TESTE (9),,,,",
                ",,Material / Apresentação,,,,,,,,,Unidade,Quantidade,,Conferência,",
                ",,DIPIRONA - 500MG (115.1),,,,,,,,,COMPR,1.234,,,",
                ",,OUTRO - 10MG (200.1),,,,,,,,,FRASC,0,,,",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        self.assertEqual(parsed["tipo_relatorio"], REPORT_TYPE_STOCK)
        self.assertEqual(parsed["metadata"]["competencia"], {"raw": "202608", "ano": 2026, "mes": 8})
        self.assertEqual(parsed["metadata"]["ups"]["id_unidade_gmus"], "9")
        self.assertEqual(len(parsed["records"]), 2)
        self.assertEqual(parsed["records"][0]["medicamento"]["codigo_gmus"], "115.1")
        self.assertEqual(parsed["records"][0]["quantidade"], Decimal("1234"))
        self.assertEqual(parsed["records"][1]["quantidade"], Decimal("0"))
        self.assertEqual(parsed["inconsistencies"], [])

    def test_rejects_competence_range(self):
        source = "\n".join(
            [
                "Consulta de Estoque",
                "Filtros: Competência Inicial: 202607 Competência Final: 202608 UPS: FARMACIA TESTE / 1234567 (9)",
                "Unidade: FARMACIA TESTE (9)",
                "Material / Apresentação,Unidade,Quantidade",
                "DIPIRONA - 500MG (115.1),COMPR,10",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        self.assertTrue(
            any(item["type"] == "competencia_intervalo" for item in parsed["inconsistencies"])
        )

    def test_parses_stock_report_without_ups_code(self):
        source = "\n".join(
            [
                "Consulta de Estoque,,,,",
                "Filtros: Competência Inicial: 202601 Competência Final: 202601 UPS: FARMACIA TESTE (9) Estoque Zerado: Ambos,,,,",
                "Unidade: FARMACIA TESTE (9),,,,",
                "Material / Apresentação,Unidade,Quantidade",
                "DIPIRONA - 500MG (115.1),COMPR,10",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        self.assertEqual(parsed["tipo_relatorio"], REPORT_TYPE_STOCK)
        self.assertEqual(parsed["metadata"]["ups"]["id_unidade_gmus"], "9")
        self.assertIsNone(parsed["metadata"]["ups"]["codigo_gmus"])
        self.assertEqual(len(parsed["records"]), 1)

    def test_parses_synthetic_movement_report(self):
        source = "\n".join(
            [
                "Movimentação de Estoque - Sintético",
                "Filtros: Data Inicial: 01/08/2026. Data Final: 31/08/2026. UPS: FARMACIA TESTE (9).",
                "UPS: FARMACIA TESTE (9)",
                ",Material,,,,,Saídas,,Compras,,,,,Transferências,,Acertos,,,Saldo Atual",
                ",,,,,Saída,Devolução,Compra,,,,,Devolução,Entrada,Saída,Entrada,Saída,,,",
                ",DIPIRONA - 500MG (115.1),,,,,10,2,25,,,,,3,4,5,6,7,,,99",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        self.assertEqual(parsed["tipo_relatorio"], REPORT_TYPE_MOVEMENT)
        self.assertEqual(parsed["metadata"]["competencia"], {"raw": "202608", "ano": 2026, "mes": 8})
        self.assertEqual(len(parsed["records"]), 1)
        self.assertEqual(parsed["records"][0]["movimentacoes"]["compra"], Decimal("25"))
        self.assertEqual(parsed["records"][0]["movimentacoes"]["saldo_atual"], Decimal("99"))
        self.assertEqual(parsed["inconsistencies"], [])

    def test_parses_shifted_movement_columns_after_page_break(self):
        source = "\n".join(
            [
                "Movimentação de Estoque - Sintético",
                "Filtros: Data Inicial: 01/08/2026. Data Final: 31/08/2026. UPS: FARMACIA TESTE (9).",
                "UPS: FARMACIA TESTE (9)",
                ",Material,,,,,Saídas,,Compras,,,,,Transferências,,Acertos,,,Saldo Atual",
                ",VERAPAMIL - 80MG (179.1),,,,,,90,0,0,,,,,0,600,0,,0,0,,,600",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        movement = parsed["records"][0]["movimentacoes"]
        self.assertEqual(movement["saida"], Decimal("90"))
        self.assertEqual(movement["transferencia_entrada"], Decimal("600"))
        self.assertEqual(movement["transferencia_saida"], Decimal("0"))
        self.assertEqual(movement["saldo_atual"], Decimal("600"))
        self.assertEqual(parsed["inconsistencies"], [])

    def test_reassembles_movement_material_split_across_pages(self):
        source = "\n".join(
            [
                "Movimentação de Estoque - Sintético",
                "Filtros: Data Inicial: 01/08/2026. Data Final: 31/08/2026. UPS: FARMACIA TESTE (9).",
                "UPS: FARMACIA TESTE (9)",
                ",Material,,,,,Saídas,,Compras,,,,,Transferências,,Acertos,,,Saldo Atual",
                ",RETINOL + COLECALCIFEROL - ,,,,,15,0,0,,,,,0,0,0,0,0,,,144",
                ",,,,Relatório emitido pelo sistema G-MUS,,,,,,,,,,,,,,,,",
                ",50.000UI + 10.000UI/ML (117.1),,,,,,,,,,,,,,,,,,,",
                ",\"COLAGENASE + CLORANFENICOL - 0,6U + 0,01G\",,,,,22,0,0,,,,,0,0,0,0,0,,,255",
                ",(206.1),,,,,,,,,,,,,,,,,,,",
            ]
        ).encode("utf-8")

        parsed = parse_report_csv(source)

        self.assertEqual(len(parsed["records"]), 2)
        first, second = parsed["records"]
        self.assertEqual(first["medicamento"]["codigo_gmus"], "117.1")
        self.assertEqual(first["movimentacoes"]["saida"], Decimal("15"))
        self.assertEqual(first["movimentacoes"]["saldo_atual"], Decimal("144"))
        self.assertEqual(second["medicamento"]["codigo_gmus"], "206.1")
        self.assertEqual(second["movimentacoes"]["saida"], Decimal("22"))
        self.assertEqual(second["movimentacoes"]["saldo_atual"], Decimal("255"))
        self.assertEqual(parsed["inconsistencies"], [])
