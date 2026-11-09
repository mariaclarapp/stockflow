from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("importacoes", "0009_importacao_alertas_relevantes"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssociacaoMaterial",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("chave", models.CharField(max_length=64)),
                ("medicamento", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="associacoes_material_importado",
                    to="medicamentos.medicamento",
                )),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("chave", "medicamento"),
                        name="unique_associacao_material_medicamento",
                    ),
                ],
            },
        ),
    ]
