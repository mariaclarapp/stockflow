from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Competencia, LocalizacaoEstoque, Ups
from .serializers import (
    CompetenciaSerializer,
    LocalizacaoEstoqueSerializer,
    UpsSerializer,
)


class UpsViewSet(ReadOnlyModelViewSet):
    queryset = Ups.objects.all()
    serializer_class = UpsSerializer


class CompetenciaViewSet(ReadOnlyModelViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer


class LocalizacaoEstoqueViewSet(ReadOnlyModelViewSet):
    queryset = LocalizacaoEstoque.objects.all()
    serializer_class = LocalizacaoEstoqueSerializer
