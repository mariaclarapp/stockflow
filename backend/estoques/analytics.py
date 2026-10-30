from collections import defaultdict
from decimal import Decimal

from django.db import models

from core.models import Competencia
from importacoes.models import Importacao, MovimentacaoEstoque
from importacoes.report_types import REPORT_TYPE_MOVEMENT


ZERO = Decimal("0.000")


def competencia_key(competencia):
    return competencia.ano * 100 + competencia.mes


def competencia_payload(competencia):
    return {
        "id": competencia.pk,
        "ano": competencia.ano,
        "mes": competencia.mes,
    }


def periodo_query(inicial, final):
    return (
        models.Q(competencia__ano__gt=inicial.ano)
        | models.Q(
            competencia__ano=inicial.ano,
            competencia__mes__gte=inicial.mes,
        )
    ) & (
        models.Q(competencia__ano__lt=final.ano)
        | models.Q(
            competencia__ano=final.ano,
            competencia__mes__lte=final.mes,
        )
    )


class AnaliseConsumoService:
    """Aggregate monthly consumption using only the G-MUS `saida` field."""

    @classmethod
    def executar(
        cls,
        *,
        competencia_inicial,
        competencia_final,
        ups_id=None,
        busca="",
        subgrupo_id=None,
        classificacao_id=None,
    ):
        competencias = list(
            Competencia.objects.filter(
                models.Q(ano__gt=competencia_inicial.ano)
                | models.Q(
                    ano=competencia_inicial.ano,
                    mes__gte=competencia_inicial.mes,
                ),
                models.Q(ano__lt=competencia_final.ano)
                | models.Q(
                    ano=competencia_final.ano,
                    mes__lte=competencia_final.mes,
                ),
            ).order_by("ano", "mes")
        )

        queryset = MovimentacaoEstoque.objects.filter(
            periodo_query(competencia_inicial, competencia_final)
        ).select_related("competencia", "ups", "medicamento")
        if ups_id:
            queryset = queryset.filter(ups_id=ups_id)
        if busca:
            queryset = queryset.filter(
                models.Q(medicamento__descricao__icontains=busca)
                | models.Q(medicamento__codigo_gmus__icontains=busca)
            )
        if subgrupo_id:
            queryset = queryset.filter(medicamento__subgrupo_gmus_id=subgrupo_id)
        if classificacao_id:
            queryset = queryset.filter(
                medicamento__classificacoes__id=classificacao_id
            ).distinct()

        movimentos = list(queryset)
        importacoes = Importacao.objects.filter(
            periodo_query(competencia_inicial, competencia_final),
            tipo_relatorio=REPORT_TYPE_MOVEMENT,
        )
        if ups_id:
            importacoes = importacoes.filter(ups_id=ups_id)
        meses_com_dados_ids = set(
            importacoes.values_list("competencia_id", flat=True).distinct()
        )
        quantidade_meses_com_dados = len(meses_com_dados_ids)

        consumo_total = ZERO
        entradas_total = ZERO
        saidas_operacionais_total = ZERO
        por_competencia = defaultdict(lambda: {
            "consumo": ZERO,
            "entradas": ZERO,
            "saidas_operacionais": ZERO,
        })
        por_medicamento = {}
        por_ups = {}

        for movimento in movimentos:
            consumo = movimento.saida
            entradas = (
                movimento.compra
                + movimento.transferencia_devolucao
                + movimento.transferencia_entrada
                + movimento.acerto_entrada
            )
            saidas_operacionais = (
                movimento.saida
                + movimento.devolucao_saida
                + movimento.transferencia_saida
                + movimento.acerto_saida
            )

            consumo_total += consumo
            entradas_total += entradas
            saidas_operacionais_total += saidas_operacionais

            competencia_totais = por_competencia[movimento.competencia_id]
            competencia_totais["consumo"] += consumo
            competencia_totais["entradas"] += entradas
            competencia_totais["saidas_operacionais"] += saidas_operacionais

            medicamento_totais = por_medicamento.setdefault(
                movimento.medicamento_id,
                {
                    "id": movimento.medicamento_id,
                    "codigo_gmus": movimento.medicamento.codigo_gmus,
                    "descricao": movimento.medicamento.descricao,
                    "unidade": movimento.medicamento.unidade,
                    "consumo": ZERO,
                },
            )
            medicamento_totais["consumo"] += consumo

            ups_totais = por_ups.setdefault(
                movimento.ups_id,
                {
                    "id": movimento.ups_id,
                    "nome": movimento.ups.nome,
                    "consumo": ZERO,
                },
            )
            ups_totais["consumo"] += consumo

        evolucao = []
        for competencia in competencias:
            totais = por_competencia[competencia.pk]
            evolucao.append(
                {
                    "competencia": competencia_payload(competencia),
                    "tem_dados": competencia.pk in meses_com_dados_ids,
                    **totais,
                }
            )

        ranking = sorted(
            por_medicamento.values(),
            key=lambda item: (-item["consumo"], item["descricao"]),
        )
        for item in ranking:
            item["media_mensal"] = (
                item["consumo"] / quantidade_meses_com_dados
                if quantidade_meses_com_dados
                else ZERO
            )
            item["participacao_percentual"] = (
                item["consumo"] * Decimal("100") / consumo_total
                if consumo_total
                else ZERO
            )

        sem_consumo = [item for item in ranking if item["consumo"] == ZERO]
        ranking_com_consumo = [item for item in ranking if item["consumo"] > ZERO]
        competencias_sem_dados = [
            competencia_payload(item)
            for item in competencias
            if item.pk not in meses_com_dados_ids
        ]

        return {
            "periodo": {
                "inicial": competencia_payload(competencia_inicial),
                "final": competencia_payload(competencia_final),
            },
            "resumo": {
                "consumo_total": consumo_total,
                "media_mensal": (
                    consumo_total / quantidade_meses_com_dados
                    if quantidade_meses_com_dados
                    else ZERO
                ),
                "medicamentos_com_consumo": len(ranking_com_consumo),
                "medicamentos_sem_consumo": len(sem_consumo),
                "entradas_total": entradas_total,
                "saidas_operacionais_total": saidas_operacionais_total,
                "saldo_movimentacoes": entradas_total - saidas_operacionais_total,
                "maior_consumo": ranking_com_consumo[0] if ranking_com_consumo else None,
            },
            "qualidade": {
                "competencias_no_periodo": len(competencias),
                "competencias_com_dados": quantidade_meses_com_dados,
                "competencias_sem_dados": competencias_sem_dados,
            },
            "evolucao": evolucao,
            "ranking": ranking_com_consumo,
            "por_ups": sorted(
                por_ups.values(),
                key=lambda item: (-item["consumo"], item["nome"]),
            ),
            "sem_consumo": sem_consumo,
        }


def variacao_percentual(atual, anterior):
    if anterior == ZERO:
        return ZERO if atual == ZERO else None
    return (atual - anterior) * Decimal("100") / anterior
