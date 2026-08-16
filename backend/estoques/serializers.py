from rest_framework import serializers

from core.serializers import CompetenciaSerializer, UpsSerializer
from importacoes.serializers import ImportacaoSerializer
from medicamentos.serializers import MedicamentoSerializer

from .models import Estoque, Lote


class LoteSerializer(serializers.ModelSerializer):
    medicamento = MedicamentoSerializer(read_only=True)

    class Meta:
        model = Lote
        fields = ["id", "medicamento", "codigo_lote", "data_validade"]


class EstoqueSerializer(serializers.ModelSerializer):
    medicamento = MedicamentoSerializer(read_only=True)
    ups = UpsSerializer(read_only=True)
    competencia = CompetenciaSerializer(read_only=True)
    lote = LoteSerializer(read_only=True)
    importacao = ImportacaoSerializer(read_only=True)

    class Meta:
        model = Estoque
        fields = [
            "id",
            "medicamento",
            "ups",
            "competencia",
            "lote",
            "importacao",
            "quantidade",
        ]
