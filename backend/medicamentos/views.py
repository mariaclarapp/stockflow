from django_filters import rest_framework as django_filters
from django.shortcuts import get_object_or_404
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .domain import descricao_possui_marcador_manipulado, nome_classificacao_manipulado
from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .serializers import (
    ClassificacaoSerializer,
    MedicamentoSerializer,
    MedicamentoClassificacaoSerializer,
    MedicamentoPublicoSerializer,
    PrincipioAtivoSerializer,
    SubgrupoGmusSerializer,
)
from .services import DisponibilidadePublicaService, EstoqueTotalAdministrativoService


class SubgrupoGmusViewSet(ReadOnlyModelViewSet):
    queryset = SubgrupoGmus.objects.all()
    serializer_class = SubgrupoGmusSerializer


class PrincipioAtivoViewSet(ReadOnlyModelViewSet):
    queryset = PrincipioAtivo.objects.all()
    serializer_class = PrincipioAtivoSerializer


class ClassificacaoViewSet(ModelViewSet):
    queryset = Classificacao.objects.all()
    serializer_class = ClassificacaoSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        classificacao = self.get_object()
        if nome_classificacao_manipulado(classificacao.nome):
            return Response(
                {"erro": "A classificacao MANIPULADO nao pode ser excluida."},
                status=status.HTTP_409_CONFLICT,
            )
        if classificacao.medicamentos.exists():
            return Response(
                {
                    "erro": (
                        "Remova as associacoes com medicamentos antes de excluir "
                        "esta classificacao."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        classificacao.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def get_queryset(self):
        return EstoqueTotalAdministrativoService.anotar_quantidade(
            super().get_queryset()
        )

    @action(detail=True, methods=["post"], url_path="classificacoes")
    def associar_classificacao(self, request, pk=None):
        medicamento = self.get_object()
        entrada = MedicamentoClassificacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        classificacao = get_object_or_404(
            Classificacao,
            pk=entrada.validated_data["classificacao_id"],
        )
        if not classificacao.ativo:
            raise ValidationError(
                {"classificacao_id": "Uma classificacao inativa nao pode ser associada."}
            )

        medicamento.classificacoes.add(classificacao)
        medicamento._prefetched_objects_cache = {}
        return Response(MedicamentoSerializer(medicamento).data)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"classificacoes/(?P<classificacao_id>[^/.]+)",
    )
    def desassociar_classificacao(self, request, classificacao_id=None, pk=None):
        medicamento = self.get_object()
        classificacao = get_object_or_404(Classificacao, pk=classificacao_id)
        if not medicamento.classificacoes.filter(pk=classificacao.pk).exists():
            raise NotFound("A classificacao nao esta associada a este medicamento.")
        if (
            nome_classificacao_manipulado(classificacao.nome)
            and descricao_possui_marcador_manipulado(medicamento.descricao)
        ):
            raise ValidationError(
                "MANIPULADO nao pode ser removida enquanto a descricao contiver "
                "o marcador (MANIPULADO)."
            )

        medicamento.classificacoes.remove(classificacao)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MedicamentoPublicoListAPIView(ListAPIView):
    serializer_class = MedicamentoPublicoSerializer
    permission_classes = [AllowAny]
    filter_backends = [drf_filters.SearchFilter]
    search_fields = ["descricao", "codigo_gmus"]

    def get_queryset(self):
        queryset = Medicamento.objects.only("codigo_gmus", "descricao", "unidade")
        return DisponibilidadePublicaService.anotar_disponibilidade(queryset)
