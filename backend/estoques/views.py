from django_filters import rest_framework as django_filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Estoque, Lote
from .serializers import EstoqueSerializer, LoteSerializer


class LoteViewSet(ReadOnlyModelViewSet):
    queryset = Lote.objects.select_related("medicamento", "medicamento__subgrupo_gmus")
    serializer_class = LoteSerializer


class EstoqueFilter(django_filters.FilterSet):
    ups = django_filters.NumberFilter(field_name="ups_id")
    ups_codigo = django_filters.CharFilter(field_name="ups__codigo_gmus")
    competencia = django_filters.NumberFilter(field_name="competencia_id")
    subgrupo = django_filters.NumberFilter(
        field_name="medicamento__subgrupo_gmus_id"
    )

    class Meta:
        model = Estoque
        fields = []


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
