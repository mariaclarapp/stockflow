from rest_framework import serializers

from .models import Competencia, Ups


class UpsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ups
        fields = ["id", "codigo_gmus", "nome"]


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = ["id", "mes", "ano"]
