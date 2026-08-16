from django.conf import settings
from django.db import models


class Importacao(models.Model):
    nome_arquivo = models.CharField(max_length=255)
    tipo_relatorio = models.CharField(max_length=80, blank=True)
    data_importacao = models.DateTimeField()
    status = models.CharField(max_length=50)
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
        verbose_name = "importacao"
        verbose_name_plural = "importacoes"

    def __str__(self):
        return f"{self.nome_arquivo} - {self.competencia} - {self.ups}"
