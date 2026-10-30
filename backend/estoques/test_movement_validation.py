from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase

from .services import calcular_validacao_movimentacao


def movement(**overrides):
    values = {
        "compra": Decimal("0"),
        "transferencia_devolucao": Decimal("0"),
        "transferencia_entrada": Decimal("0"),
        "acerto_entrada": Decimal("0"),
        "saida": Decimal("0"),
        "devolucao_saida": Decimal("0"),
        "transferencia_saida": Decimal("0"),
        "acerto_saida": Decimal("0"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class MovementValidationTests(TestCase):
    def test_missing_movement_means_zero_when_both_stocks_exist(self):
        result = calcular_validacao_movimentacao(
            medicamento={"id": 1},
            movimentacao=None,
            estoque_anterior=Decimal("25"),
            estoque_atual=Decimal("25"),
        )

        self.assertEqual(result["situacao"], "conferido")
        self.assertTrue(result["movimentacao_ausente"])
        self.assertEqual(result["entradas"], Decimal("0"))
        self.assertEqual(result["saidas"], Decimal("0"))

    def test_new_medicine_uses_zero_as_previous_stock(self):
        result = calcular_validacao_movimentacao(
            medicamento={"id": 1},
            movimentacao=movement(
                compra=Decimal("1800"),
                saida=Decimal("480"),
            ),
            estoque_anterior=None,
            estoque_atual=Decimal("1320"),
        )

        self.assertEqual(result["situacao"], "conferido")
        self.assertTrue(result["estoque_anterior_inferido"])
        self.assertEqual(result["estoque_anterior"], Decimal("0"))
        self.assertEqual(result["estoque_esperado"], Decimal("1320"))

    def test_item_without_current_stock_is_not_comparable(self):
        result = calcular_validacao_movimentacao(
            medicamento={"id": 1},
            movimentacao=movement(saida=Decimal("10")),
            estoque_anterior=Decimal("10"),
            estoque_atual=None,
        )

        self.assertEqual(result["situacao"], "sem_base_completa")
