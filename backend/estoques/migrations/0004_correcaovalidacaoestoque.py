from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0005_alter_ups_id_unidade_gmus"),
        ("estoques", "0003_saldoestoque"),
        ("medicamentos", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CorrecaoValidacaoEstoque",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("versao_estoque_anterior", models.CharField(max_length=180)),
                ("versao_movimentacao", models.CharField(max_length=180)),
                ("versao_estoque_final", models.CharField(max_length=180)),
                ("estoque_observado_original", models.DecimalField(decimal_places=3, max_digits=14)),
                ("estoque_corrigido", models.DecimalField(decimal_places=3, max_digits=14)),
                ("justificativa", models.TextField(max_length=1000)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("competencia", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correcoes_validacao_estoque", to="core.competencia")),
                ("corrigido_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correcoes_validacao_estoque", to=settings.AUTH_USER_MODEL)),
                ("medicamento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correcoes_validacao_estoque", to="medicamentos.medicamento")),
                ("ups", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="correcoes_validacao_estoque", to="core.ups")),
            ],
            options={
                "verbose_name": "correcao manual de validacao de estoque",
                "verbose_name_plural": "correcoes manuais de validacao de estoque",
                "ordering": ["-atualizado_em", "-id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("medicamento", "versao_estoque_anterior", "versao_movimentacao", "versao_estoque_final"),
                        name="unique_correcao_validacao_por_fontes",
                    )
                ],
            },
        ),
    ]
