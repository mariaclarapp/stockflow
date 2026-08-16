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
