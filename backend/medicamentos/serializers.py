import re

from rest_framework import serializers

from .domain import CLASSIFICACAO_MANIPULADO, nome_classificacao_manipulado
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
    def validate_nome(self, value):
        nome = value.strip()
        if not nome:
            raise serializers.ValidationError("O nome da classificacao e obrigatorio.")

        if nome_classificacao_manipulado(nome):
            nome = CLASSIFICACAO_MANIPULADO

        if (
            self.instance
            and nome_classificacao_manipulado(self.instance.nome)
            and nome != self.instance.nome
        ):
            raise serializers.ValidationError(
                "A classificacao MANIPULADO nao pode ser renomeada."
            )

        existentes = Classificacao.objects.filter(nome__iexact=nome)
        if self.instance:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise serializers.ValidationError(
                "Ja existe uma classificacao com este nome."
            )
        return nome

    def validate_cor(self, value):
        cor = value.strip()
        if cor and not re.fullmatch(
            r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})",
            cor,
        ):
            raise serializers.ValidationError(
                "Informe uma cor hexadecimal valida, como #0B8178."
            )
        return cor

    def validate(self, attrs):
        nome = attrs.get("nome", getattr(self.instance, "nome", ""))
        ativo = attrs.get("ativo", getattr(self.instance, "ativo", True))
        if nome_classificacao_manipulado(nome) and not ativo:
            raise serializers.ValidationError(
                {"ativo": "A classificacao MANIPULADO deve permanecer ativa."}
            )
        return attrs

    class Meta:
        model = Classificacao
        fields = ["id", "nome", "cor", "descricao", "ativo"]


class MedicamentoClassificacaoSerializer(serializers.Serializer):
    classificacao_id = serializers.IntegerField(min_value=1)


class MedicamentoSerializer(serializers.ModelSerializer):
    subgrupo_gmus = SubgrupoGmusSerializer(read_only=True)
    principios_ativos = PrincipioAtivoSerializer(many=True, read_only=True)
    classificacoes = ClassificacaoSerializer(many=True, read_only=True)
    quantidade_estoque_total = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        read_only=True,
        allow_null=True,
    )

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
            "quantidade_estoque_total",
        ]


class MedicamentoPublicoSerializer(serializers.ModelSerializer):
    disponibilidade = serializers.CharField(read_only=True)

    class Meta:
        model = Medicamento
        fields = ["codigo_gmus", "descricao", "unidade", "disponibilidade"]
