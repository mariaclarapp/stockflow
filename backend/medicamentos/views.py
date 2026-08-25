from django_filters import rest_framework as django_filters
from django.db.models import Case, Exists, IntegerField, OuterRef, When
from django.shortcuts import get_object_or_404
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .domain import (
    CLASSIFICACAO_MANIPULADO,
    descricao_possui_marcador_manipulado,
    nome_classificacao_manipulado,
)
from .models import Classificacao, Medicamento, PrincipioAtivo, SubgrupoGmus
from .serializers import (
    ClassificacaoSerializer,
    MedicamentoSerializer,
    MedicamentoClassificacaoSerializer,
    MedicamentoClassificacaoLoteSerializer,
    MedicamentoComparacaoSerializer,
    MedicamentoPublicoSerializer,
    PrincipioAtivoSerializer,
    SubgrupoGmusSerializer,
)
from .services import (
    DesclassificacaoMedicamentosLoteService,
    DisponibilidadePublicaService,
    EstoqueTotalAdministrativoService,
    MedicamentoComparacaoService,
    ClassificacaoMedicamentosLoteService,
    normalizar_ids_medicamentos,
)


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
    ids = django_filters.CharFilter(method="filter_ids")
    sem_categoria = django_filters.BooleanFilter(method="filter_sem_categoria")
    subgrupo = django_filters.NumberFilter(field_name="subgrupo_gmus_id")
    classificacao = django_filters.NumberFilter(
        field_name="classificacoes__id",
        distinct=True,
    )

    class Meta:
        model = Medicamento
        fields = []

    def filter_ids(self, queryset, name, value):
        try:
            ids = normalizar_ids_medicamentos(value)
        except ValueError as error:
            raise ValidationError({name: str(error)}) from error

        ordem = Case(
            *[
                When(pk=medicamento_id, then=posicao)
                for posicao, medicamento_id in enumerate(ids)
            ],
            output_field=IntegerField(),
        )
        return queryset.filter(pk__in=ids).order_by(ordem)

    def filter_sem_categoria(self, queryset, name, value):
        if not value:
            return queryset
        categoria_manual = Classificacao.objects.filter(
            medicamentos=OuterRef("pk")
        ).exclude(nome__iexact=CLASSIFICACAO_MANIPULADO)
        return queryset.filter(subgrupo_gmus__isnull=True).annotate(
            tem_categoria_manual=Exists(categoria_manual)
        ).filter(tem_categoria_manual=False)

    def filter_queryset(self, queryset):
        dados = self.form.cleaned_data
        if dados.get("sem_categoria") and (
            dados.get("subgrupo") is not None
            or dados.get("classificacao") is not None
        ):
            raise ValidationError(
                {
                    "sem_categoria": (
                        "Não combine sem_categoria com subgrupo ou classificacao."
                    )
                }
            )
        return super().filter_queryset(queryset)


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

    @action(detail=False, methods=["get"], url_path="comparacao")
    def comparacao(self, request):
        try:
            ids = normalizar_ids_medicamentos(request.query_params.get("ids", ""))
        except ValueError as error:
            raise ValidationError({"ids": str(error)}) from error

        resultado = MedicamentoComparacaoService.construir(ids)
        competencia = resultado["competencia"]
        ups = resultado["ups"]
        medicamentos = MedicamentoComparacaoSerializer(
            resultado["medicamentos"],
            many=True,
            context={
                "competencia_disponivel": competencia is not None,
                "ups": ups,
                "quantidades": resultado["quantidades"],
            },
        ).data
        return Response(
            {
                "competencia": (
                    {
                        "id": competencia.pk,
                        "mes": competencia.mes,
                        "ano": competencia.ano,
                    }
                    if competencia is not None
                    else None
                ),
                "ups": [
                    {
                        "id": item.pk,
                        "nome": item.nome,
                        "id_unidade_gmus": item.id_unidade_gmus,
                    }
                    for item in ups
                ],
                "medicamentos": medicamentos,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="classificacoes/lote",
    )
    def classificar_lote(self, request):
        entrada = MedicamentoClassificacaoLoteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        classificacao = get_object_or_404(
            Classificacao,
            pk=entrada.validated_data["classificacao_id"],
        )
        if not classificacao.ativo:
            raise ValidationError(
                {"classificacao_id": "A classificação deve estar ativa."}
            )
        if nome_classificacao_manipulado(classificacao.nome):
            raise ValidationError(
                {
                    "classificacao_id": (
                        "MANIPULADO não pode ser aplicada como categoria em lote."
                    )
                }
            )

        resumo = ClassificacaoMedicamentosLoteService.aplicar(
            entrada.validated_data["medicamento_ids"],
            classificacao,
        )
        return Response(resumo)

    @action(
        detail=False,
        methods=["post"],
        url_path="classificacoes/lote/remover",
    )
    def desclassificar_lote(self, request):
        entrada = MedicamentoClassificacaoLoteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        classificacao = get_object_or_404(
            Classificacao,
            pk=entrada.validated_data["classificacao_id"],
        )
        if nome_classificacao_manipulado(classificacao.nome):
            raise ValidationError(
                {
                    "classificacao_id": (
                        "MANIPULADO não pode ser removida como categoria em lote."
                    )
                }
            )

        resumo = DesclassificacaoMedicamentosLoteService.remover(
            entrada.validated_data["medicamento_ids"],
            classificacao,
        )
        return Response(resumo)

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
