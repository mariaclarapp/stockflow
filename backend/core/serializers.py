from rest_framework import serializers

from .models import Competencia, Ups


class UpsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ups
        fields = [
            "id",
            "codigo_gmus",
            "id_unidade_gmus",
            "nome",
            "participa_competencia",
            "compoe_estoque_convencional",
        ]


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = ["id", "mes", "ano"]


class DashboardCompetenciaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    completa = serializers.BooleanField()


class DashboardUpsTotaisSerializer(serializers.Serializer):
    participantes = serializers.IntegerField()
    importadas = serializers.IntegerField()


class DashboardImportacaoUpsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codigo_gmus = serializers.CharField()
    id_unidade_gmus = serializers.CharField()
    nome = serializers.CharField()


class DashboardImportacaoSerializer(serializers.Serializer):
    ups = DashboardImportacaoUpsSerializer()
    status = serializers.CharField()
    data_importacao = serializers.DateTimeField()
    registros_estoque = serializers.IntegerField()


class DashboardTotaisSerializer(serializers.Serializer):
    medicamentos = serializers.IntegerField()
    estoques = serializers.IntegerField()


class DashboardResumoSerializer(serializers.Serializer):
    competencia_atual = DashboardCompetenciaSerializer(allow_null=True)
    ups = DashboardUpsTotaisSerializer()
    importacoes = DashboardImportacaoSerializer(many=True)
    totais = DashboardTotaisSerializer()


class CompetenciaUpsSituacaoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codigo_gmus = serializers.CharField()
    id_unidade_gmus = serializers.CharField()
    nome = serializers.CharField()
    importada = serializers.BooleanField()
    status = serializers.CharField(allow_null=True)
    data_importacao = serializers.DateTimeField(allow_null=True)
    registros_estoque = serializers.IntegerField(allow_null=True)


class CompetenciaUpsResumoSerializer(serializers.Serializer):
    esperadas = serializers.IntegerField()
    importadas_validas = serializers.IntegerField()
    situacoes = CompetenciaUpsSituacaoSerializer(many=True)


class CompetenciaAcompanhamentoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    completa = serializers.BooleanField()
    ups = CompetenciaUpsResumoSerializer()


class CompetenciaMaisRecenteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()


class CompetenciasAcompanhamentoSerializer(serializers.Serializer):
    competencia_completa_mais_recente = CompetenciaMaisRecenteSerializer(
        allow_null=True
    )
    competencias = CompetenciaAcompanhamentoSerializer(many=True)
