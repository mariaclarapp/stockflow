from django_filters import rest_framework as django_filters
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from medicamentos.models import Medicamento

from .models import Estoque, Lote
from .serializers import (
    EstoqueSerializer,
    HistoricoMedicamentoSerializer,
    LoteSerializer,
)
from .services import HistoricoMedicamentoService


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
        model = Estoque
        fields = []

    def reject_ambiguous_ups_code(self, queryset, name, value):
        raise ValidationError(
            "O filtro ups_codigo e ambiguo; utilize ups com o ID da UPS no StockFlow."
        )


class EstoqueViewSet(ReadOnlyModelViewSet):
    queryset = Estoque.objects.select_related(
        "medicamento",
        "medicamento__subgrupo_gmus",
        "ups",
        "competencia",
        "lote",
        "lote__medicamento",
        "lote__medicamento__subgrupo_gmus",
        "importacao",
        "importacao__competencia",
        "importacao__ups",
        "importacao__usuario",
    ).prefetch_related(
        "medicamento__principios_ativos",
        "medicamento__classificacoes",
        "lote__medicamento__principios_ativos",
        "lote__medicamento__classificacoes",
    )
    serializer_class = EstoqueSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = EstoqueFilter


class HistoricoMedicamentoAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        medicamento = get_object_or_404(Medicamento.objects.only("id"), pk=pk)
        resultado = HistoricoMedicamentoService.construir(medicamento.pk)
        serializer = HistoricoMedicamentoSerializer(resultado)
        return Response(serializer.data)
