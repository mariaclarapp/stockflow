from rest_framework import serializers

from core.serializers import CompetenciaSerializer, UpsSerializer

from .models import Importacao


class ImportacaoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)
    competencia = CompetenciaSerializer(read_only=True)
    ups = UpsSerializer(read_only=True)

    class Meta:
        model = Importacao
        fields = [
            "id",
            "nome_arquivo",
            "hash_arquivo",
            "tipo_relatorio",
            "data_importacao",
            "status",
            "usuario",
            "competencia",
            "ups",
        ]
