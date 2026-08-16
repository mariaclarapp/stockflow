from django.db import models


class SubgrupoGmus(models.Model):
    codigo_gmus = models.PositiveIntegerField(null=True, blank=True, unique=True)
    nome = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nome", "codigo_gmus"]
        verbose_name = "subgrupo GMUS"
        verbose_name_plural = "subgrupos GMUS"

    def __str__(self):
        if self.codigo_gmus is None:
            return self.nome or "Subgrupo GMUS"
        return f"{self.codigo_gmus} - {self.nome}" if self.nome else str(self.codigo_gmus)


class PrincipioAtivo(models.Model):
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["nome"]
        verbose_name = "principio ativo"
        verbose_name_plural = "principios ativos"

    def __str__(self):
        return self.nome


class Classificacao(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    cor = models.CharField(max_length=20, blank=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "classificacao"
        verbose_name_plural = "classificacoes"

    def __str__(self):
        return self.nome


class Medicamento(models.Model):
    codigo_gmus = models.CharField(max_length=50, unique=True)
    descricao = models.TextField()
    unidade = models.CharField(max_length=80, blank=True)
    subgrupo_gmus = models.ForeignKey(
        SubgrupoGmus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicamentos",
    )
    principios_ativos = models.ManyToManyField(
        PrincipioAtivo,
        blank=True,
        related_name="medicamentos",
    )
    classificacoes = models.ManyToManyField(
        Classificacao,
        blank=True,
        related_name="medicamentos",
    )

    class Meta:
        ordering = ["descricao", "codigo_gmus"]
        verbose_name = "medicamento"
        verbose_name_plural = "medicamentos"

    def __str__(self):
        return f"{self.codigo_gmus} - {self.descricao}"
