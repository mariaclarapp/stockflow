from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_ups_id_unidade_gmus_alter_ups_codigo_gmus_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ups",
            name="id_unidade_gmus",
            field=models.CharField(max_length=50),
        ),
    ]
