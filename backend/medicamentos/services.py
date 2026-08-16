from decimal import Decimal

from django.db.models import (
    Case,
    CharField,
    Count,
    DecimalField,
    Exists,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from core.models import Competencia, Ups
from estoques.models import Estoque
from importacoes.models import Importacao

from .models import Classificacao


class DisponibilidadePublicaService:
    DISPONIVEL_MANIPULADO = (
        "Disponível sob manipulação, confirmar disponibilidade"
    )
    DISPONIVEL = "Disponível"
    INDISPONIVEL = "Indisponível"
    NAO_INFORMADA = "Disponibilidade não informada"
    TIPO_RELATORIO_INVENTARIO = "inventario"
    STATUS_IMPORTACAO_VALIDOS = (
        Importacao.Status.CONCLUIDA,
        Importacao.Status.CONCLUIDA_COM_ALERTAS,
    )

    @classmethod
    def identificar_competencia_completa(cls):
        total_ups_participantes = Ups.objects.filter(
            participa_competencia=True
        ).count()
        if total_ups_participantes == 0:
            return None

        return (
            Competencia.objects.annotate(
                total_ups_importadas=Count(
                    "importacoes__ups",
                    filter=Q(
                        importacoes__tipo_relatorio=cls.TIPO_RELATORIO_INVENTARIO,
                        importacoes__status__in=cls.STATUS_IMPORTACAO_VALIDOS,
                        importacoes__ups__participa_competencia=True,
                    ),
                    distinct=True,
                )
            )
            .filter(total_ups_importadas=total_ups_participantes)
            .order_by("-ano", "-mes")
            .first()
        )

    @classmethod
    def anotar_disponibilidade(cls, queryset):
        competencia = cls.identificar_competencia_completa()
        tag_manipulado_ativa = Classificacao.objects.filter(
            nome="MANIPULADO",
            ativo=True,
            medicamentos=OuterRef("pk"),
        )
        queryset = queryset.annotate(
            tem_tag_manipulado=Exists(tag_manipulado_ativa)
        )

        if competencia is None:
            return queryset.annotate(
                disponibilidade=Case(
                    When(
                        tem_tag_manipulado=True,
                        then=Value(cls.DISPONIVEL_MANIPULADO),
                    ),
                    default=Value(cls.NAO_INFORMADA),
                    output_field=CharField(),
                )
            )

        campo_saldo = DecimalField(max_digits=14, decimal_places=3)
        saldo_convencional = (
            Estoque.objects.filter(
                medicamento_id=OuterRef("pk"),
                competencia=competencia,
                ups__compoe_estoque_convencional=True,
            )
            .values("medicamento_id")
            .annotate(total=Sum("quantidade"))
            .values("total")[:1]
        )

        return queryset.annotate(
            saldo_convencional=Coalesce(
                Subquery(saldo_convencional, output_field=campo_saldo),
                Value(Decimal("0.000"), output_field=campo_saldo),
            )
        ).annotate(
            disponibilidade=Case(
                When(
                    tem_tag_manipulado=True,
                    then=Value(cls.DISPONIVEL_MANIPULADO),
                ),
                When(
                    saldo_convencional__gt=0,
                    then=Value(cls.DISPONIVEL),
                ),
                default=Value(cls.INDISPONIVEL),
                output_field=CharField(),
            )
        )
