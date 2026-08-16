from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Estoque, Lote
from .serializers import EstoqueSerializer, LoteSerializer


class LoteViewSet(ReadOnlyModelViewSet):
    queryset = Lote.objects.select_related("medicamento", "medicamento__subgrupo_gmus")
    serializer_class = LoteSerializer


class EstoqueViewSet(ReadOnlyModelViewSet):
    queryset = Estoque.objects.select_related(
        "medicamento",
        "medicamento__subgrupo_gmus",
        "ups",
        "competencia",
        "lote",
        "lote__medicamento",
        "lote__medicamento__subgrupo_gmus",
        "localizacao",
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
