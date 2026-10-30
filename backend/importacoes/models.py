from django.conf import settings
from django.db import models


class Importacao(models.Model):
    class Status(models.TextChoices):
        CONCLUIDA = "concluida", "Concluida"
        CONCLUIDA_COM_ALERTAS = "concluida_com_alertas", "Concluida com alertas"
        CONCLUIDA_PARCIAL = "concluida_parcial", "Concluida parcial"

    nome_arquivo = models.CharField(max_length=255)
    hash_arquivo = models.CharField(max_length=64, blank=True)
    tipo_relatorio = models.CharField(max_length=80, blank=True)
    data_importacao = models.DateTimeField()
    status = models.CharField(max_length=50, choices=Status.choices)
    quantidade_nao_associada = models.DecimalField(
        max_digits=14, decimal_places=3, default=0
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="importacoes",
    )
    competencia = models.ForeignKey(
        "core.Competencia",
        on_delete=models.PROTECT,
        related_name="importacoes",
    )
    ups = models.ForeignKey(
        "core.Ups",
        on_delete=models.PROTECT,
        related_name="importacoes",
    )

    class Meta:
        ordering = ["-data_importacao", "nome_arquivo"]
        constraints = [
            models.UniqueConstraint(
                fields=["competencia", "ups", "tipo_relatorio"],
                name="unique_importacao_competencia_ups_tipo",
            )
        ]
        verbose_name = "importacao"
        verbose_name_plural = "importacoes"

    def __str__(self):
        return f"{self.nome_arquivo} - {self.competencia} - {self.ups}"


class MovimentacaoEstoque(models.Model):
    importacao = models.ForeignKey(
        Importacao,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
    )
    medicamento = models.ForeignKey(
        "medicamentos.Medicamento",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
    )
    ups = models.ForeignKey(
        "core.Ups",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
    )
    competencia = models.ForeignKey(
        "core.Competencia",
        on_delete=models.PROTECT,
        related_name="movimentacoes_estoque",
    )
    data_inicial = models.DateField()
    data_final = models.DateField()
    saida = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    devolucao_saida = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    compra = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    transferencia_devolucao = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    transferencia_entrada = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    transferencia_saida = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    acerto_entrada = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    acerto_saida = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    saldo_atual = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        ordering = ["medicamento__descricao", "competencia", "ups"]
        constraints = [
            models.UniqueConstraint(
                fields=["importacao", "medicamento"],
                name="unique_movimentacao_importacao_medicamento",
            )
        ]
