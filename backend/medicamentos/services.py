from decimal import Decimal

from django.db.models import (
    Case,
    CharField,
    DecimalField,
    Exists,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from core.services import CompetenciaService
from estoques.models import Estoque

from .domain import CLASSIFICACAO_MANIPULADO
from .models import Classificacao


class EstoqueTotalAdministrativoService:
    @classmethod
    def anotar_quantidade(cls, queryset):
        competencia = CompetenciaService.identificar_competencia_completa()
        campo_quantidade = DecimalField(max_digits=14, decimal_places=3)

        if competencia is None:
            return queryset.annotate(
                quantidade_estoque_total=Value(None, output_field=campo_quantidade)
            )

        estoque_total = (
            Estoque.objects.filter(
                medicamento_id=OuterRef("pk"),
                competencia=competencia,
                ups__participa_competencia=True,
            )
            .values("medicamento_id")
            .annotate(total=Sum("quantidade"))
            .values("total")[:1]
        )
        return queryset.annotate(
            quantidade_estoque_total=Coalesce(
                Subquery(estoque_total, output_field=campo_quantidade),
                Value(Decimal("0.000"), output_field=campo_quantidade),
            )
        )


class DisponibilidadePublicaService:
    DISPONIVEL_MANIPULADO = (
        "Disponível sob manipulação, confirmar disponibilidade"
    )
    DISPONIVEL = "Disponível"
    INDISPONIVEL = "Indisponível"
    NAO_INFORMADA = "Disponibilidade não informada"
    @classmethod
    def anotar_disponibilidade(cls, queryset):
        competencia = CompetenciaService.identificar_competencia_completa()
        tag_manipulado_ativa = Classificacao.objects.filter(
            nome=CLASSIFICACAO_MANIPULADO,
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
