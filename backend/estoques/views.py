from decimal import Decimal

from django_filters import rest_framework as django_filters
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from medicamentos.models import Medicamento
from importacoes.models import MovimentacaoEstoque
from importacoes.report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK
from core.models import Competencia, Ups
from core.services import CompetenciaService

from .models import Lote, SaldoEstoque
from .serializers import (
    EstoqueSerializer,
    HistoricoMedicamentoSerializer,
    LoteSerializer,
    SaldoEstoqueSerializer,
)
from .services import HistoricoMedicamentoService, calcular_validacao_movimentacao
from .analytics import AnaliseConsumoService, competencia_key, variacao_percentual


class LoteViewSet(ReadOnlyModelViewSet):
    queryset = Lote.objects.select_related("medicamento", "medicamento__subgrupo_gmus")
    serializer_class = LoteSerializer


class EstoqueFilter(django_filters.FilterSet):
    medicamento = django_filters.NumberFilter(field_name="medicamento_id")
    ups = django_filters.NumberFilter(field_name="ups_id")
    ups_codigo = django_filters.CharFilter(method="reject_ambiguous_ups_code")
    competencia = django_filters.NumberFilter(field_name="competencia_id")
    subgrupo = django_filters.NumberFilter(
        field_name="medicamento__subgrupo_gmus_id"
    )

    class Meta:
        model = SaldoEstoque
        fields = []

    def reject_ambiguous_ups_code(self, queryset, name, value):
        raise ValidationError(
            "O filtro ups_codigo e ambiguo; utilize ups com o ID da UPS no StockFlow."
        )


class EstoqueViewSet(ReadOnlyModelViewSet):
    queryset = SaldoEstoque.objects.select_related(
        "medicamento",
        "medicamento__subgrupo_gmus",
        "ups",
        "competencia",
        "importacao",
        "importacao__competencia",
        "importacao__ups",
        "importacao__usuario",
    ).prefetch_related(
        "medicamento__principios_ativos",
        "medicamento__classificacoes",
    )
    serializer_class = SaldoEstoqueSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = EstoqueFilter


class SaldoEstoqueViewSet(ReadOnlyModelViewSet):
    queryset = SaldoEstoque.objects.select_related(
        "medicamento",
        "ups",
        "competencia",
        "importacao",
    )
    serializer_class = SaldoEstoqueSerializer
    permission_classes = [IsAdminUser]


class ValidacaoMovimentacoesAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        competencia_id = request.query_params.get("competencia")
        ups_id = request.query_params.get("ups")
        if not competencia_id or not ups_id:
            return Response({"erro": "Informe competencia e ups para validar as movimentacoes."}, status=400)
        competencia = get_object_or_404(Competencia, pk=competencia_id)
        ups = get_object_or_404(Ups, pk=ups_id)

        current_import = CompetenciaService.importacao_valida(
            competencia=competencia,
            ups=ups,
            tipo_relatorio=REPORT_TYPE_STOCK,
        )
        if current_import is None:
            return Response(
                {"erro": "Importe um estoque final concluido para esta competencia e UPS."},
                status=422,
            )

        movement_import = CompetenciaService.importacao_valida(
            competencia=competencia,
            ups=ups,
            tipo_relatorio=REPORT_TYPE_MOVEMENT,
        )
        if movement_import is None:
            return Response(
                {"erro": "Importe as movimentacoes concluidas desta competencia e UPS."},
                status=422,
            )

        previous_import = CompetenciaService.importacao_anterior_valida(
            competencia=competencia,
            ups=ups,
            tipo_relatorio=REPORT_TYPE_STOCK,
        )
        if previous_import is None:
            return Response(
                {"erro": "Importe um estoque anterior concluido para validar esta competencia."},
                status=422,
            )

        previous = previous_import.competencia
        movements = {
            item.medicamento_id: item
            for item in MovimentacaoEstoque.objects.filter(importacao=movement_import)
        }
        current = {
            item.medicamento_id: item.quantidade
            for item in SaldoEstoque.objects.filter(importacao=current_import)
        }
        previous_values = {
            item.medicamento_id: item.quantidade
            for item in SaldoEstoque.objects.filter(importacao=previous_import)
        }
        medicine_ids = set(movements) | set(current) | set(previous_values)
        medicines = {
            item["id"]: item
            for item in Medicamento.objects.filter(pk__in=medicine_ids).values(
                "id", "codigo_gmus", "descricao", "unidade"
            )
        }
        movement_fields = (
            "compra",
            "devolucao_saida",
            "transferencia_devolucao",
            "transferencia_entrada",
            "transferencia_saida",
            "acerto_entrada",
            "acerto_saida",
            "saida",
        )
        movement_totals = {
            field: sum(
                (getattr(item, field) for item in movements.values()),
                Decimal("0.000"),
            )
            for field in movement_fields
        }
        total_entradas = (
            movement_totals["compra"]
            + movement_totals["transferencia_devolucao"]
            + movement_totals["transferencia_entrada"]
            + movement_totals["acerto_entrada"]
        )
        total_saidas = (
            movement_totals["saida"]
            + movement_totals["devolucao_saida"]
            + movement_totals["transferencia_saida"]
            + movement_totals["acerto_saida"]
        )
        records = []
        for medicine_id in sorted(medicine_ids):
            records.append(
                calcular_validacao_movimentacao(
                    medicamento=medicines[medicine_id],
                    movimentacao=movements.get(medicine_id),
                    estoque_anterior=previous_values.get(medicine_id),
                    estoque_atual=current.get(medicine_id),
                )
            )
        comparable = [item for item in records if item["situacao"] != "sem_base_completa"]
        estoque_anterior_total = sum(
            (item["estoque_anterior"] for item in comparable), Decimal("0.000")
        )
        estoque_esperado_total = sum(
            (item["estoque_esperado"] for item in comparable), Decimal("0.000")
        )
        estoque_observado_total = sum(
            (item["estoque_observado"] for item in comparable), Decimal("0.000")
        )
        entradas_comparaveis = sum(
            (item["entradas"] for item in comparable), Decimal("0.000")
        )
        saidas_comparaveis = sum(
            (item["saidas"] for item in comparable), Decimal("0.000")
        )
        medicamentos_novos = sum(
            bool(item.get("estoque_anterior_inferido")) for item in comparable
        )
        fora_da_validacao = [
            item for item in records if item["situacao"] == "sem_base_completa"
        ]
        sem_saldo_final = sum(
            item.get("estoque_observado") is None for item in fora_da_validacao
        )
        return Response({
            "competencia": {"id": competencia.pk, "ano": competencia.ano, "mes": competencia.mes},
            "competencia_anterior": ({"id": previous.pk, "ano": previous.ano, "mes": previous.mes} if previous else None),
            "ups": {"id": ups.pk, "nome": ups.nome},
            "fontes": {
                "estoque_anterior": {
                    "importacao_id": previous_import.pk,
                    "status": previous_import.status,
                },
                "movimentacoes": {
                    "importacao_id": movement_import.pk,
                    "status": movement_import.status,
                },
                "estoque_final": {
                    "importacao_id": current_import.pk,
                    "status": current_import.status,
                },
            },
            "movimentacoes": {
                **movement_totals,
                "entradas": entradas_comparaveis,
                "saidas": saidas_comparaveis,
                "devolucoes": (
                    movement_totals["devolucao_saida"]
                    + movement_totals["transferencia_devolucao"]
                ),
                "saldo_liquido": entradas_comparaveis - saidas_comparaveis,
            },
            "movimentacoes_comparaveis": {
                "entradas": entradas_comparaveis,
                "saidas": saidas_comparaveis,
                "saldo_liquido": entradas_comparaveis - saidas_comparaveis,
            },
            "totais": {
                "registros": len(records),
                "comparaveis": len(comparable),
                "divergentes": sum(item["situacao"] == "divergente" for item in comparable),
                "medicamentos_novos": medicamentos_novos,
                "fora_da_validacao": len(fora_da_validacao),
                "sem_saldo_final": sem_saldo_final,
                "estoque_anterior": estoque_anterior_total,
                "estoque_esperado": estoque_esperado_total,
                "estoque_observado": estoque_observado_total,
                "diferenca": estoque_observado_total - estoque_esperado_total,
            },
            "registros": records,
        })


class AnaliseConsumoAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            inicial = self._competencia(request, "competencia_inicial")
            final = self._competencia(request, "competencia_final")
            self._validar_periodo(inicial, final)
            filtros = self._filtros(request)
        except ValueError as error:
            return Response({"erro": str(error)}, status=400)

        resultado = AnaliseConsumoService.executar(
            competencia_inicial=inicial,
            competencia_final=final,
            **filtros,
        )

        comparacao_inicial_id = request.query_params.get("comparacao_inicial")
        comparacao_final_id = request.query_params.get("comparacao_final")
        if bool(comparacao_inicial_id) != bool(comparacao_final_id):
            return Response(
                {"erro": "Informe o inicio e o fim do periodo de comparacao."},
                status=400,
            )
        resultado["comparacao"] = None
        if comparacao_inicial_id and comparacao_final_id:
            try:
                comparacao_inicial = self._competencia(
                    request, "comparacao_inicial"
                )
                comparacao_final = self._competencia(request, "comparacao_final")
                self._validar_periodo(comparacao_inicial, comparacao_final)
            except ValueError as error:
                return Response({"erro": str(error)}, status=400)
            comparacao = AnaliseConsumoService.executar(
                competencia_inicial=comparacao_inicial,
                competencia_final=comparacao_final,
                **filtros,
            )
            atual = resultado["resumo"]["consumo_total"]
            anterior = comparacao["resumo"]["consumo_total"]
            resultado["comparacao"] = {
                "periodo": comparacao["periodo"],
                "resumo": comparacao["resumo"],
                "evolucao": comparacao["evolucao"],
                "variacao_percentual": variacao_percentual(atual, anterior),
            }
        return Response(resultado)

    def _competencia(self, request, campo):
        valor = request.query_params.get(campo)
        if not valor or not valor.isdigit():
            raise ValueError(f"Informe {campo.replace('_', ' ')}.")
        try:
            return CompetenciaService.competencias_ativas().get(pk=valor)
        except Competencia.DoesNotExist as error:
            raise ValueError("Competencia nao encontrada.") from error

    def _validar_periodo(self, inicial, final):
        if competencia_key(inicial) > competencia_key(final):
            raise ValueError("A competencia inicial deve ser anterior a final.")

    def _filtros(self, request):
        filtros = {"busca": request.query_params.get("busca", "").strip()}
        for parametro, destino in (
            ("ups", "ups_id"),
            ("subgrupo", "subgrupo_id"),
            ("classificacao", "classificacao_id"),
        ):
            valor = request.query_params.get(parametro)
            if valor and not valor.isdigit():
                raise ValueError(f"Informe um valor valido para {parametro}.")
            filtros[destino] = int(valor) if valor else None
        return filtros


class HistoricoMedicamentoAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        medicamento = get_object_or_404(Medicamento.objects.only("id"), pk=pk)
        resultado = HistoricoMedicamentoService.construir(medicamento.pk)
        serializer = HistoricoMedicamentoSerializer(resultado)
        return Response(serializer.data)
