from django.conf import settings
from django.db import models


class Lote(models.Model):
    medicamento = models.ForeignKey(
        "medicamentos.Medicamento",
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    codigo_lote = models.CharField(max_length=120)
    data_validade = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["medicamento__descricao", "codigo_lote", "data_validade"]
        verbose_name = "lote"
        verbose_name_plural = "lotes"

    def __str__(self):
        validade = f" - {self.data_validade:%d/%m/%Y}" if self.data_validade else ""
        return f"{self.codigo_lote}{validade}"


class Estoque(models.Model):
    medicamento = models.ForeignKey(
        "medicamentos.Medicamento",
        on_delete=models.PROTECT,
        related_name="estoques",
    )
    ups = models.ForeignKey(
        "core.Ups",
        on_delete=models.PROTECT,
        related_name="estoques",
    )
    competencia = models.ForeignKey(
        "core.Competencia",
        on_delete=models.PROTECT,
        related_name="estoques",
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="estoques",
    )
    importacao = models.ForeignKey(
        "importacoes.Importacao",
        on_delete=models.PROTECT,
        related_name="estoques",
    )
    quantidade = models.DecimalField(max_digits=14, decimal_places=3)

    class Meta:
        ordering = ["medicamento__descricao", "competencia", "ups"]
        verbose_name = "estoque"
        verbose_name_plural = "estoques"

    def __str__(self):
        return f"{self.medicamento} - {self.ups} - {self.competencia}"


class SaldoEstoque(models.Model):
    medicamento = models.ForeignKey(
        "medicamentos.Medicamento",
        on_delete=models.PROTECT,
        related_name="saldos_estoque",
    )
    ups = models.ForeignKey(
        "core.Ups",
        on_delete=models.PROTECT,
        related_name="saldos_estoque",
    )
    competencia = models.ForeignKey(
        "core.Competencia",
        on_delete=models.PROTECT,
        related_name="saldos_estoque",
    )
    importacao = models.ForeignKey(
        "importacoes.Importacao",
        on_delete=models.PROTECT,
        related_name="saldos_estoque",
    )
    quantidade = models.DecimalField(max_digits=14, decimal_places=3)

    class Meta:
        ordering = ["medicamento__descricao", "competencia", "ups"]
        constraints = [
            models.UniqueConstraint(
                fields=["medicamento", "ups", "competencia", "importacao"],
                name="unique_saldo_estoque_importacao_medicamento",
            )
        ]

    def __str__(self):
        return f"{self.medicamento} - {self.ups} - {self.competencia}"


class CorrecaoValidacaoEstoque(models.Model):
    """Audited manual correction applied only to one exact validation version."""

    competencia = models.ForeignKey(
        "core.Competencia",
        on_delete=models.PROTECT,
        related_name="correcoes_validacao_estoque",
    )
    ups = models.ForeignKey(
        "core.Ups",
        on_delete=models.PROTECT,
        related_name="correcoes_validacao_estoque",
    )
    medicamento = models.ForeignKey(
        "medicamentos.Medicamento",
        on_delete=models.PROTECT,
        related_name="correcoes_validacao_estoque",
    )
    versao_estoque_anterior = models.CharField(max_length=180)
    versao_movimentacao = models.CharField(max_length=180)
    versao_estoque_final = models.CharField(max_length=180)
    estoque_observado_original = models.DecimalField(
        max_digits=14, decimal_places=3
    )
    estoque_corrigido = models.DecimalField(max_digits=14, decimal_places=3)
    justificativa = models.TextField(max_length=1000)
    corrigido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="correcoes_validacao_estoque",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "medicamento",
                    "versao_estoque_anterior",
                    "versao_movimentacao",
                    "versao_estoque_final",
                ],
                name="unique_correcao_validacao_por_fontes",
            )
        ]
        verbose_name = "correcao manual de validacao de estoque"
        verbose_name_plural = "correcoes manuais de validacao de estoque"
