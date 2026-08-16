from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Ups(models.Model):
    codigo_gmus = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["nome"]
        verbose_name = "UPS"
        verbose_name_plural = "UPS"

    def __str__(self):
        return self.nome


class Competencia(models.Model):
    mes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    ano = models.PositiveIntegerField()

    class Meta:
        ordering = ["-ano", "-mes"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(mes__gte=1) & models.Q(mes__lte=12),
                name="check_competencia_mes_entre_1_e_12",
            ),
            models.UniqueConstraint(
                fields=["ano", "mes"],
                name="unique_competencia_ano_mes",
            )
        ]
        verbose_name = "competencia"
        verbose_name_plural = "competencias"

    def __str__(self):
        return f"{self.mes:02d}/{self.ano}"
