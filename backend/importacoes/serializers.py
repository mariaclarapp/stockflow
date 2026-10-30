from pathlib import Path

from rest_framework import serializers

from core.serializers import CompetenciaSerializer, UpsSerializer

from .models import Importacao, MovimentacaoEstoque


class InventoryUploadSerializer(serializers.Serializer):
    arquivo = serializers.FileField(allow_empty_file=False, write_only=True)
    reimportar = serializers.BooleanField(default=False, required=False, write_only=True)

    def validate_arquivo(self, arquivo):
        if Path(arquivo.name).suffix.lower() != ".csv":
            raise serializers.ValidationError(
                "Envie um arquivo com extensao .csv."
            )
        return arquivo


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
            "quantidade_nao_associada",
            "usuario",
            "competencia",
            "ups",
        ]


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    medicamento = serializers.StringRelatedField(read_only=True)
    ups = UpsSerializer(read_only=True)
    competencia = CompetenciaSerializer(read_only=True)
    importacao = ImportacaoSerializer(read_only=True)

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            "id", "medicamento", "ups", "competencia", "importacao",
            "data_inicial", "data_final", "saida", "devolucao_saida",
            "compra", "transferencia_devolucao", "transferencia_entrada",
            "transferencia_saida", "acerto_entrada", "acerto_saida", "saldo_atual",
        ]
