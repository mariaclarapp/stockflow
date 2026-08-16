from rest_framework import serializers

from .models import Competencia, LocalizacaoEstoque, Ups


class UpsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ups
        fields = ["id", "codigo_gmus", "nome"]


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = ["id", "mes", "ano"]


class LocalizacaoEstoqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalizacaoEstoque
        fields = ["id", "nome"]
