from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Case,
    CharField,
    DecimalField,
    Exists,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from core.models import Ups
from core.services import CompetenciaService
from estoques.models import Estoque

from .domain import CLASSIFICACAO_MANIPULADO
from .models import Classificacao, Medicamento


MAX_MEDICAMENTOS_COMPARACAO = 50


def normalizar_ids_medicamentos(valor):
    partes = valor.split(",") if valor else []
    if not partes or any(
        not parte.isdigit() or int(parte) < 1 for parte in partes
    ):
        raise ValueError("Informe IDs inteiros positivos separados por vírgula.")

    ids = list(dict.fromkeys(int(parte) for parte in partes))
    if len(ids) > MAX_MEDICAMENTOS_COMPARACAO:
        raise ValueError(
            f"Selecione no máximo {MAX_MEDICAMENTOS_COMPARACAO} medicamentos."
        )
    return ids


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


class MedicamentoComparacaoService:
    @classmethod
    def construir(cls, ids):
        ups_participantes = list(
            Ups.objects.filter(participa_competencia=True).order_by("id")
        )
        competencia = CompetenciaService.identificar_competencia_completa(
            total_ups_participantes=len(ups_participantes)
        )
        ordem = Case(
            *[
                When(pk=medicamento_id, then=posicao)
                for posicao, medicamento_id in enumerate(ids)
            ],
            output_field=IntegerField(),
        )
        medicamentos = list(
            Medicamento.objects.filter(pk__in=ids)
            .select_related("subgrupo_gmus")
            .prefetch_related("classificacoes")
            .order_by(ordem)
        )

        quantidades = {}
        if competencia is not None and medicamentos:
            linhas = (
                Estoque.objects.filter(
                    competencia=competencia,
                    medicamento_id__in=[item.pk for item in medicamentos],
                    ups_id__in=[ups.pk for ups in ups_participantes],
                )
                .values("medicamento_id", "ups_id")
                .annotate(quantidade=Sum("quantidade"))
            )
            quantidades = {
                (linha["medicamento_id"], linha["ups_id"]): linha["quantidade"]
                for linha in linhas
            }

        return {
            "competencia": competencia,
            "ups": ups_participantes if competencia is not None else [],
            "medicamentos": medicamentos,
            "quantidades": quantidades,
        }


class ClassificacaoMedicamentosLoteService:
    @classmethod
    @transaction.atomic
    def aplicar(cls, medicamento_ids, classificacao):
        medicamentos = list(
            Medicamento.objects.select_for_update()
            .filter(pk__in=medicamento_ids)
            .prefetch_related("classificacoes")
        )
        medicamentos_por_id = {item.pk: item for item in medicamentos}
        ignorados_subgrupo = []
        ignorados_ja_classificados = []
        elegiveis = []

        for medicamento_id in medicamento_ids:
            medicamento = medicamentos_por_id.get(medicamento_id)
            if medicamento is None:
                continue
            if medicamento.subgrupo_gmus_id is not None:
                ignorados_subgrupo.append(medicamento_id)
                continue
            possui_categoria_manual = any(
                item.nome.upper() != CLASSIFICACAO_MANIPULADO
                for item in medicamento.classificacoes.all()
            )
            if possui_categoria_manual:
                ignorados_ja_classificados.append(medicamento_id)
                continue
            elegiveis.append(medicamento_id)

        cls._criar_associacoes(elegiveis, classificacao.pk)
        inexistentes = [
            item for item in medicamento_ids if item not in medicamentos_por_id
        ]
        return {
            "selecionados": len(medicamento_ids),
            "classificados": len(elegiveis),
            "ignorados_subgrupo": len(ignorados_subgrupo),
            "ignorados_ja_classificados": len(ignorados_ja_classificados),
            "ignorados_inexistentes": len(inexistentes),
        }

    @staticmethod
    def _criar_associacoes(medicamento_ids, classificacao_id):
        associacao = Medicamento.classificacoes.through
        associacao.objects.bulk_create(
            [
                associacao(
                    medicamento_id=medicamento_id,
                    classificacao_id=classificacao_id,
                )
                for medicamento_id in medicamento_ids
            ]
        )


class DesclassificacaoMedicamentosLoteService:
    @classmethod
    @transaction.atomic
    def remover(cls, medicamento_ids, classificacao):
        medicamentos = list(
            Medicamento.objects.select_for_update()
            .filter(pk__in=medicamento_ids)
            .prefetch_related("classificacoes")
        )
        medicamentos_por_id = {item.pk: item for item in medicamentos}
        ignorados_subgrupo = []
        ignorados_sem_classificacao = []
        elegiveis = []

        for medicamento_id in medicamento_ids:
            medicamento = medicamentos_por_id.get(medicamento_id)
            if medicamento is None:
                continue
            if medicamento.subgrupo_gmus_id is not None:
                ignorados_subgrupo.append(medicamento_id)
                continue
            classificacao_ids = {
                item.pk for item in medicamento.classificacoes.all()
            }
            if classificacao.pk not in classificacao_ids:
                ignorados_sem_classificacao.append(medicamento_id)
                continue
            elegiveis.append(medicamento_id)

        cls._remover_associacoes(elegiveis, classificacao.pk)
        inexistentes = [
            item for item in medicamento_ids if item not in medicamentos_por_id
        ]
        return {
            "selecionados": len(medicamento_ids),
            "desclassificados": len(elegiveis),
            "ignorados_subgrupo": len(ignorados_subgrupo),
            "ignorados_sem_classificacao": len(ignorados_sem_classificacao),
            "ignorados_inexistentes": len(inexistentes),
        }

    @staticmethod
    def _remover_associacoes(medicamento_ids, classificacao_id):
        Medicamento.classificacoes.through.objects.filter(
            medicamento_id__in=medicamento_ids,
            classificacao_id=classificacao_id,
        ).delete()


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
