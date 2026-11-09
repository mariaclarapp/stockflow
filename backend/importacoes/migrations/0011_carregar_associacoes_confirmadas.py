from hashlib import sha256
import unicodedata

from django.db import migrations


def carregar_associacoes_confirmadas(apps, schema_editor):
    Pendencia = apps.get_model("importacoes", "PendenciaImportacao")
    Associacao = apps.get_model("importacoes", "AssociacaoMaterial")
    database = schema_editor.connection.alias
    resolvidas = Pendencia.objects.using(database).filter(
        status="resolvida",
        medicamento_id__isnull=False,
        tipo="medicamento_sem_codigo",
        importacao__tipo_relatorio="estoque",
    ).order_by().values_list("descricao", "unidade", "medicamento_id")

    for descricao, unidade, medicamento_id in resolvidas.iterator():
        fields = [
            unicodedata.normalize("NFC", " ".join(value.split()).casefold())
            for value in (descricao, unidade)
        ]
        chave = sha256("\0".join(fields).encode("utf-8")).hexdigest()
        Associacao.objects.using(database).get_or_create(
            chave=chave,
            medicamento_id=medicamento_id,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("importacoes", "0010_associacao_material"),
    ]

    operations = [
        migrations.RunPython(carregar_associacoes_confirmadas, migrations.RunPython.noop),
    ]
