from rest_framework import serializers

from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus


class SubgrupoGmusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubgrupoGmus
        fields = ["id", "codigo_gmus", "nome"]


class PrincipioAtivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrincipioAtivo
        fields = ["id", "nome"]


class ClassificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classificacao
        fields = ["id", "nome", "cor", "descricao", "ativo"]


class MedicamentoSerializer(serializers.ModelSerializer):
    subgrupo_gmus = SubgrupoGmusSerializer(read_only=True)
    principios_ativos = PrincipioAtivoSerializer(many=True, read_only=True)
    classificacoes = ClassificacaoSerializer(many=True, read_only=True)

    class Meta:
        model = Medicamento
        fields = [
            "id",
            "codigo_gmus",
            "descricao",
            "unidade",
            "subgrupo_gmus",
            "principios_ativos",
            "classificacoes",
        ]


class MedicamentoPublicoSerializer(serializers.ModelSerializer):
    disponibilidade = serializers.CharField(read_only=True)

    class Meta:
        model = Medicamento
        fields = ["codigo_gmus", "descricao", "unidade", "disponibilidade"]
