from rest_framework import filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .serializers import (
    ClassificacaoSerializer,
    MedicamentoSerializer,
    PrincipioAtivoSerializer,
    SubgrupoGmusSerializer,
)


class SubgrupoGmusViewSet(ReadOnlyModelViewSet):
    queryset = SubgrupoGmus.objects.all()
    serializer_class = SubgrupoGmusSerializer


class PrincipioAtivoViewSet(ReadOnlyModelViewSet):
    queryset = PrincipioAtivo.objects.all()
    serializer_class = PrincipioAtivoSerializer


class ClassificacaoViewSet(ReadOnlyModelViewSet):
    queryset = Classificacao.objects.all()
    serializer_class = ClassificacaoSerializer


class MedicamentoViewSet(ReadOnlyModelViewSet):
    queryset = Medicamento.objects.select_related("subgrupo_gmus").prefetch_related(
        "principios_ativos",
        "classificacoes",
    )
    serializer_class = MedicamentoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["descricao", "codigo_gmus"]
