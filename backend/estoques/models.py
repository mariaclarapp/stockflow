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
