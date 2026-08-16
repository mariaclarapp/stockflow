from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Competencia, Ups
from .serializers import CompetenciaSerializer, UpsSerializer


class UpsViewSet(ReadOnlyModelViewSet):
    queryset = Ups.objects.all()
    serializer_class = UpsSerializer


class CompetenciaViewSet(ReadOnlyModelViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer
