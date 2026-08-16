from django_filters import rest_framework as django_filters
from rest_framework import filters as drf_filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .serializers import (
    ClassificacaoSerializer,
    MedicamentoSerializer,
    MedicamentoPublicoSerializer,
    PrincipioAtivoSerializer,
    SubgrupoGmusSerializer,
)
from .services import DisponibilidadePublicaService


class SubgrupoGmusViewSet(ReadOnlyModelViewSet):
    queryset = SubgrupoGmus.objects.all()
    serializer_class = SubgrupoGmusSerializer


class PrincipioAtivoViewSet(ReadOnlyModelViewSet):
    queryset = PrincipioAtivo.objects.all()
    serializer_class = PrincipioAtivoSerializer


class ClassificacaoViewSet(ReadOnlyModelViewSet):
    queryset = Classificacao.objects.all()
    serializer_class = ClassificacaoSerializer


class MedicamentoFilter(django_filters.FilterSet):
    subgrupo = django_filters.NumberFilter(field_name="subgrupo_gmus_id")

    class Meta:
        model = Medicamento
        fields = []


class MedicamentoViewSet(ReadOnlyModelViewSet):
    queryset = Medicamento.objects.select_related("subgrupo_gmus").prefetch_related(
        "principios_ativos",
        "classificacoes",
    )
    serializer_class = MedicamentoSerializer
    filter_backends = [
        drf_filters.SearchFilter,
        django_filters.DjangoFilterBackend,
    ]
    filterset_class = MedicamentoFilter
    search_fields = ["descricao", "codigo_gmus"]


class MedicamentoPublicoListAPIView(ListAPIView):
    serializer_class = MedicamentoPublicoSerializer
    permission_classes = [AllowAny]
    filter_backends = [drf_filters.SearchFilter]
    search_fields = ["descricao", "codigo_gmus"]

    def get_queryset(self):
        queryset = Medicamento.objects.only("codigo_gmus", "descricao", "unidade")
        return DisponibilidadePublicaService.anotar_disponibilidade(queryset)
