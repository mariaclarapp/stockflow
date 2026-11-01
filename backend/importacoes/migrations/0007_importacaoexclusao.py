from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0005_alter_ups_id_unidade_gmus"),
        ("importacoes", "0006_importacao_quantidade_nao_associada"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportacaoExclusao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("importacao_id_original", models.PositiveBigIntegerField(db_index=True)),
                ("nome_arquivo", models.CharField(max_length=255)),
                ("hash_arquivo", models.CharField(blank=True, max_length=64)),
                ("tipo_relatorio", models.CharField(max_length=80)),
                ("status_original", models.CharField(max_length=50)),
                ("data_exclusao", models.DateTimeField(auto_now_add=True)),
                ("contagens", models.JSONField(default=dict)),
                ("competencia", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="auditorias_exclusao_importacao", to="core.competencia")),
                ("excluida_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="exclusoes_de_importacao", to=settings.AUTH_USER_MODEL)),
                ("ups", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="auditorias_exclusao_importacao", to="core.ups")),
                ("usuario_importacao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="importacoes_posteriormente_excluidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "auditoria de exclusao de importacao",
                "verbose_name_plural": "auditorias de exclusao de importacao",
                "ordering": ["-data_exclusao", "-id"],
            },
        ),
    ]
