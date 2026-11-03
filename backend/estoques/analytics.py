from collections import defaultdict
from decimal import Decimal

from django.db import models

from core.models import Competencia, Ups
from core.services import CompetenciaService
from importacoes.models import MovimentacaoEstoque
from importacoes.report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK
from medicamentos.models import Medicamento

from .models import SaldoEstoque


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
        unidade="",
        subgrupo_id=None,
        classificacao_id=None,
    ):
        competencias = list(
            CompetenciaService.competencias_ativas().filter(
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

        importacoes = CompetenciaService.importacoes_validas(
            REPORT_TYPE_MOVEMENT
        ).filter(periodo_query(competencia_inicial, competencia_final))
        if ups_id:
            importacoes = importacoes.filter(ups_id=ups_id)
            ups_esperadas = 1
        else:
            importacoes = importacoes.filter(ups__participa_competencia=True)
            ups_esperadas = Ups.objects.filter(participa_competencia=True).count()

        cobertura_por_competencia = {
            item["competencia_id"]: item["total_ups"]
            for item in importacoes.values("competencia_id").annotate(
                total_ups=models.Count("ups_id", distinct=True)
            )
        }
        meses_com_dados_ids = {
            competencia.pk
            for competencia in competencias
            if ups_esperadas > 0
            and cobertura_por_competencia.get(competencia.pk, 0) >= ups_esperadas
        }
        quantidade_meses_com_dados = len(meses_com_dados_ids)

        queryset = MovimentacaoEstoque.objects.filter(
            importacao__in=importacoes,
            competencia_id__in=meses_com_dados_ids,
        ).select_related("competencia", "ups", "medicamento")
        if busca:
            queryset = queryset.filter(
                models.Q(medicamento__descricao__icontains=busca)
                | models.Q(medicamento__codigo_gmus__icontains=busca)
            )
        if unidade:
            queryset = queryset.filter(medicamento__unidade__iexact=unidade)
        if subgrupo_id:
            queryset = queryset.filter(medicamento__subgrupo_gmus_id=subgrupo_id)
        if classificacao_id:
            queryset = queryset.filter(
                medicamento__classificacoes__id=classificacao_id
            ).distinct()

        movimentos = list(queryset)

        importacoes_estoque_final = CompetenciaService.importacoes_validas(
            REPORT_TYPE_STOCK
        ).filter(competencia=competencia_final)
        if ups_id:
            importacoes_estoque_final = importacoes_estoque_final.filter(ups_id=ups_id)
            ups_estoque_esperadas = 1
        else:
            importacoes_estoque_final = importacoes_estoque_final.filter(
                ups__participa_competencia=True
            )
            ups_estoque_esperadas = ups_esperadas
        estoque_final_completo = (
            ups_estoque_esperadas > 0
            and importacoes_estoque_final.values("ups_id").distinct().count()
            >= ups_estoque_esperadas
        )
        saldos_finais = SaldoEstoque.objects.filter(
            importacao__in=importacoes_estoque_final
        )
        saldos_por_medicamento = defaultdict(lambda: ZERO)
        if estoque_final_completo:
            for saldo in saldos_finais.values("medicamento_id").annotate(
                total=models.Sum("quantidade")
            ):
                saldos_por_medicamento[saldo["medicamento_id"]] = saldo["total"]

        medicamento_ids = {item.medicamento_id for item in movimentos}
        medicamento_ids.update(
            saldos_finais.values_list("medicamento_id", flat=True)
        )
        medicamentos = Medicamento.objects.filter(pk__in=medicamento_ids)
        if busca:
            medicamentos = medicamentos.filter(
                models.Q(descricao__icontains=busca)
                | models.Q(codigo_gmus__icontains=busca)
            )
        if unidade:
            medicamentos = medicamentos.filter(unidade__iexact=unidade)
        if subgrupo_id:
            medicamentos = medicamentos.filter(subgrupo_gmus_id=subgrupo_id)
        if classificacao_id:
            medicamentos = medicamentos.filter(
                classificacoes__id=classificacao_id
            ).distinct()
        medicamentos = list(medicamentos)
        medicamento_ids_filtrados = {item.pk for item in medicamentos}
        movimentos = [
            item for item in movimentos
            if item.medicamento_id in medicamento_ids_filtrados
        ]

        consumo_total = ZERO
        entradas_total = ZERO
        saidas_operacionais_total = ZERO
        por_competencia = defaultdict(lambda: {
            "consumo": ZERO,
            "entradas": ZERO,
            "saidas_operacionais": ZERO,
        })
        por_medicamento = {
            medicamento.pk: {
                "id": medicamento.pk,
                "codigo_gmus": medicamento.codigo_gmus,
                "descricao": medicamento.descricao,
                "unidade": medicamento.unidade,
                "consumo": ZERO,
                "estoque_atual": (
                    saldos_por_medicamento[medicamento.pk]
                    if estoque_final_completo
                    else None
                ),
            }
            for medicamento in medicamentos
        }
        por_medicamento_competencia = defaultdict(
            lambda: defaultdict(lambda: ZERO)
        )
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

            medicamento_totais = por_medicamento[movimento.medicamento_id]
            medicamento_totais["consumo"] += consumo
            por_medicamento_competencia[movimento.medicamento_id][
                movimento.competencia_id
            ] += consumo

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
        participacao_acumulada = ZERO
        for item in ranking:
            item["media_mensal"] = (
                item["consumo"] / quantidade_meses_com_dados
                if quantidade_meses_com_dados
                else ZERO
            )
            item["evolucao"] = [
                {
                    "competencia": competencia_payload(competencia),
                    "tem_dados": competencia.pk in meses_com_dados_ids,
                    "consumo": por_medicamento_competencia[item["id"]][
                        competencia.pk
                    ],
                }
                for competencia in competencias
            ]
            meses_com_consumo = sum(
                ponto["consumo"] > ZERO for ponto in item["evolucao"]
            )
            item["meses_com_consumo"] = meses_com_consumo
            item["media_meses_com_consumo"] = (
                item["consumo"] / meses_com_consumo
                if meses_com_consumo
                else ZERO
            )
            pontos_com_dados = [
                ponto for ponto in item["evolucao"] if ponto["tem_dados"]
            ]
            item["pico_consumo"] = (
                max(pontos_com_dados, key=lambda ponto: ponto["consumo"])
                if pontos_com_dados
                else None
            )
            item["participacao_percentual"] = (
                item["consumo"] * Decimal("100") / consumo_total
                if consumo_total
                else ZERO
            )
            if item["consumo"] > ZERO:
                participacao_anterior = participacao_acumulada
                participacao_acumulada += item["participacao_percentual"]
                item["participacao_acumulada"] = participacao_acumulada
                if participacao_anterior < Decimal("80"):
                    item["classe_abc"] = "A"
                elif participacao_anterior < Decimal("95"):
                    item["classe_abc"] = "B"
                else:
                    item["classe_abc"] = "C"
            else:
                item["participacao_acumulada"] = participacao_acumulada
                item["classe_abc"] = None

            media_mensal = item["media_mensal"]
            estoque_atual = item["estoque_atual"]
            item["meses_cobertura"] = (
                estoque_atual / media_mensal
                if estoque_atual is not None and media_mensal > ZERO
                else None
            )
            item["dias_cobertura"] = (
                item["meses_cobertura"] * Decimal("30")
                if item["meses_cobertura"] is not None
                else None
            )

            if len(pontos_com_dados) >= 2:
                consumo_inicial = pontos_com_dados[0]["consumo"]
                consumo_final = pontos_com_dados[-1]["consumo"]
                item["tendencia_percentual"] = variacao_percentual(
                    consumo_final, consumo_inicial
                )
                if consumo_final > consumo_inicial:
                    item["tendencia"] = "alta"
                elif consumo_final < consumo_inicial:
                    item["tendencia"] = "queda"
                else:
                    item["tendencia"] = "estavel"
            else:
                item["tendencia_percentual"] = None
                item["tendencia"] = "sem_base"

        sem_consumo = [item for item in ranking if item["consumo"] == ZERO]
        ranking_com_consumo = [item for item in ranking if item["consumo"] > ZERO]
        competencias_sem_dados = [
            competencia_payload(item)
            for item in competencias
            if item.pk not in meses_com_dados_ids
        ]
        curva_abc = [
            {
                "classe": classe,
                "medicamentos": sum(
                    item["classe_abc"] == classe for item in ranking_com_consumo
                ),
                "consumo": sum(
                    (
                        item["consumo"]
                        for item in ranking_com_consumo
                        if item["classe_abc"] == classe
                    ),
                    ZERO,
                ),
            }
            for classe in ("A", "B", "C")
        ]
        estoque_atual_total = (
            sum((item["estoque_atual"] for item in ranking), ZERO)
            if estoque_final_completo
            else None
        )

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
                "estoque_atual": estoque_atual_total,
                "estoque_final_completo": estoque_final_completo,
            },
            "qualidade": {
                "competencias_no_periodo": len(competencias),
                "competencias_com_dados": quantidade_meses_com_dados,
                "competencias_sem_dados": competencias_sem_dados,
                "ups_esperadas": ups_esperadas,
                "cobertura_por_competencia": [
                    {
                        "competencia": competencia_payload(competencia),
                        "ups_importadas": cobertura_por_competencia.get(
                            competencia.pk, 0
                        ),
                        "ups_esperadas": ups_esperadas,
                        "completa": competencia.pk in meses_com_dados_ids,
                    }
                    for competencia in competencias
                ],
            },
            "evolucao": evolucao,
            "ranking": ranking_com_consumo,
            "por_ups": sorted(
                por_ups.values(),
                key=lambda item: (-item["consumo"], item["nome"]),
            ),
            "sem_consumo": sem_consumo,
            "curva_abc": curva_abc,
        }


def variacao_percentual(atual, anterior):
    if anterior == ZERO:
        return ZERO if atual == ZERO else None
    return (atual - anterior) * Decimal("100") / anterior
