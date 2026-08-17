from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Competencia, Ups
from .serializers import (
    CompetenciaSerializer,
    DashboardResumoSerializer,
    UpsSerializer,
)
from .services import DashboardResumoService


class UpsViewSet(ReadOnlyModelViewSet):
    queryset = Ups.objects.all()
    serializer_class = UpsSerializer


class CompetenciaViewSet(ReadOnlyModelViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer


class DashboardResumoAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        resumo = DashboardResumoService.construir()
        serializer = DashboardResumoSerializer(resumo)
        return Response(serializer.data)
