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


class CompetenciaHistoricoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    completa = serializers.BooleanField()


class LoteHistoricoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codigo_lote = serializers.CharField()
    data_validade = serializers.DateField(allow_null=True)


class RegistroEstoqueHistoricoSerializer(serializers.Serializer):
    estoque_id = serializers.IntegerField()
    quantidade = serializers.DecimalField(max_digits=18, decimal_places=3)
    lote = LoteHistoricoSerializer(allow_null=True)


class UpsHistoricoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codigo_gmus = serializers.CharField()
    id_unidade_gmus = serializers.CharField()
    nome = serializers.CharField()


class UpsEstoqueAtualSerializer(UpsHistoricoSerializer):
    compoe_estoque_convencional = serializers.BooleanField()


class EstoqueAtualPorUpsSerializer(serializers.Serializer):
    ups = UpsEstoqueAtualSerializer()
    quantidade_total = serializers.DecimalField(max_digits=18, decimal_places=3)
    registros = RegistroEstoqueHistoricoSerializer(many=True)


class HistoricoPorUpsSerializer(serializers.Serializer):
    ups = UpsHistoricoSerializer()
    quantidade_total = serializers.DecimalField(max_digits=18, decimal_places=3)


class EstoqueAtualSerializer(serializers.Serializer):
    competencia = CompetenciaHistoricoSerializer()
    quantidade_consolidada_convencional = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )
    por_ups = EstoqueAtualPorUpsSerializer(many=True)


class CompetenciaEstoqueHistoricoSerializer(serializers.Serializer):
    competencia = CompetenciaHistoricoSerializer()
    quantidade_consolidada_convencional = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )
    por_ups = HistoricoPorUpsSerializer(many=True)


class HistoricoMedicamentoSerializer(serializers.Serializer):
    medicamento_id = serializers.IntegerField()
    estoque_atual = EstoqueAtualSerializer(allow_null=True)
    historico = CompetenciaEstoqueHistoricoSerializer(many=True)
