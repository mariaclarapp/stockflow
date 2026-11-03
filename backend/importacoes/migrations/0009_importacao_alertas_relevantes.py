from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("importacoes", "0008_pendenciaimportacao_importacao_erros_nao_corrigiveis"),
    ]

    operations = [
        migrations.AddField(
            model_name="importacao",
            name="alertas_relevantes",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
