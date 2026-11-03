import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("importacoes", "0007_importacaoexclusao"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="importacao",
            name="erros_nao_corrigiveis",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="PendenciaImportacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("linha", models.PositiveIntegerField()),
                ("tipo", models.CharField(default="medicamento_sem_codigo", max_length=80)),
                ("descricao", models.TextField()),
                ("unidade", models.CharField(blank=True, max_length=80)),
                ("quantidade", models.DecimalField(decimal_places=3, max_digits=14)),
                ("raw", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("resolvida", "Resolvida")], default="pendente", max_length=20)),
                ("resolvida_em", models.DateTimeField(blank=True, null=True)),
                ("importacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pendencias", to="importacoes.importacao")),
                ("medicamento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pendencias_importacao_resolvidas", to="medicamentos.medicamento")),
                ("resolvida_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pendencias_importacao_resolvidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "pendencia de importacao",
                "verbose_name_plural": "pendencias de importacao",
                "ordering": ["linha", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="pendenciaimportacao",
            constraint=models.UniqueConstraint(fields=("importacao", "linha", "tipo"), name="unique_pendencia_importacao_linha_tipo"),
        ),
    ]
