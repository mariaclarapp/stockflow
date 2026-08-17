from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Competencia, Ups
from .serializers import (
    CompetenciaSerializer,
    CompetenciasAcompanhamentoSerializer,
    DashboardResumoSerializer,
    UpsSerializer,
)
from .services import CompetenciasAcompanhamentoService, DashboardResumoService


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


class CompetenciasAcompanhamentoAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        acompanhamento = CompetenciasAcompanhamentoService.construir()
        serializer = CompetenciasAcompanhamentoSerializer(acompanhamento)
        return Response(serializer.data)
