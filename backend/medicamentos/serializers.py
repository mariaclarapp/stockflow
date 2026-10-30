import re

from rest_framework import serializers

from .domain import CLASSIFICACAO_MANIPULADO, nome_classificacao_manipulado
from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .services import MAX_MEDICAMENTOS_COMPARACAO


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


class MedicamentoClassificacaoLoteSerializer(serializers.Serializer):
    medicamento_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=MAX_MEDICAMENTOS_COMPARACAO,
    )
    classificacao_id = serializers.IntegerField(min_value=1)

    def validate_medicamento_ids(self, value):
        return list(dict.fromkeys(value))


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
    competencia_estoque = serializers.SerializerMethodField()
    estoque_por_ups = serializers.SerializerMethodField()
    situacao_estoque = serializers.SerializerMethodField()
    situacao_validacao = serializers.SerializerMethodField()

    def get_competencia_estoque(self, medicamento):
        competencia = self.context.get("competencia_estoque")
        if competencia is None:
            return None
        return {
            "id": competencia.pk,
            "mes": competencia.mes,
            "ano": competencia.ano,
        }

    def get_estoque_por_ups(self, medicamento):
        competencia = self.context.get("competencia_estoque")
        if competencia is None:
            return []

        quantidades = {}
        for saldo in getattr(medicamento, "saldos_listagem", []):
            quantidades[saldo.ups_id] = (
                quantidades.get(saldo.ups_id, 0) + saldo.quantidade
            )

        return [
            {
                "ups_id": ups.pk,
                "ups_nome": ups.nome,
                "id_unidade_gmus": ups.id_unidade_gmus,
                "quantidade": f"{quantidades.get(ups.pk, 0):.3f}",
            }
            for ups in self.context.get("ups_estoque", [])
        ]

    def get_situacao_estoque(self, medicamento):
        if not self.context.get("dados_estoque_disponiveis", False):
            return "sem_dados"
        quantidade = getattr(medicamento, "quantidade_estoque_total", None)
        if quantidade is None:
            return "sem_dados"
        return "disponivel" if quantidade > 0 else "sem_estoque"

    def get_situacao_validacao(self, medicamento):
        return self.context.get("situacoes_validacao", {}).get(
            medicamento.pk,
            "nao_validado",
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
            "competencia_estoque",
            "estoque_por_ups",
            "situacao_estoque",
            "situacao_validacao",
        ]


class MedicamentoComparacaoSerializer(serializers.ModelSerializer):
    subgrupo_gmus = SubgrupoGmusSerializer(read_only=True)
    classificacoes = ClassificacaoSerializer(many=True, read_only=True)
    quantidade_estoque_total = serializers.SerializerMethodField()
    estoque_por_ups = serializers.SerializerMethodField()

    def get_quantidade_estoque_total(self, medicamento):
        if not self.context["competencia_disponivel"]:
            return None
        total = sum(
            (
                self.context["quantidades"].get((medicamento.pk, ups.pk), 0)
                for ups in self.context["ups"]
            ),
            start=0,
        )
        return f"{total:.3f}"

    def get_estoque_por_ups(self, medicamento):
        if not self.context["competencia_disponivel"]:
            return []
        return [
            {
                "ups_id": ups.pk,
                "quantidade": f"{self.context['quantidades'].get((medicamento.pk, ups.pk), 0):.3f}",
            }
            for ups in self.context["ups"]
        ]

    class Meta:
        model = Medicamento
        fields = [
            "id",
            "codigo_gmus",
            "descricao",
            "unidade",
            "subgrupo_gmus",
            "classificacoes",
            "quantidade_estoque_total",
            "estoque_por_ups",
        ]


class MedicamentoPublicoSerializer(serializers.ModelSerializer):
    disponibilidade = serializers.CharField(read_only=True)

    class Meta:
        model = Medicamento
        fields = ["codigo_gmus", "descricao", "unidade", "disponibilidade"]
