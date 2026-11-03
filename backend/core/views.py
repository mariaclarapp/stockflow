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
from .services import (
    CompetenciaService,
    CompetenciasAcompanhamentoService,
    DashboardResumoService,
)


class UpsViewSet(ReadOnlyModelViewSet):
    serializer_class = UpsSerializer

    def get_queryset(self):
        return Ups.objects.filter(
            importacoes__tipo_relatorio__in=CompetenciaService.TIPOS_RELATORIO_ATIVOS,
        ).distinct().order_by("nome")


class CompetenciaViewSet(ReadOnlyModelViewSet):
    serializer_class = CompetenciaSerializer

    def get_queryset(self):
        return CompetenciaService.competencias_ativas().order_by("-ano", "-mes")


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
