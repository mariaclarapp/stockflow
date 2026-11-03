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

from core.models import Competencia, Ups
from core.services import CompetenciaService
from estoques.models import SaldoEstoque
from importacoes.report_types import REPORT_TYPE_STOCK

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
    SituacaoValidacaoMedicamentosService,
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

    def _competencia_estoque(self):
        if hasattr(self, "_competencia_estoque_cache"):
            return self._competencia_estoque_cache

        competencia_id = self.request.query_params.get("competencia")
        if competencia_id:
            if not competencia_id.isdigit():
                raise ValidationError({"competencia": "Informe uma competencia valida."})
            competencia = get_object_or_404(
                CompetenciaService.competencias_ativas(), pk=competencia_id
            )
        else:
            competencia = EstoqueTotalAdministrativoService.competencia_padrao()
        self._competencia_estoque_cache = competencia
        return competencia

    def _ups_estoque(self):
        if hasattr(self, "_ups_estoque_cache"):
            return self._ups_estoque_cache

        ups_id = self.request.query_params.get("ups")
        participantes = Ups.objects.filter(participa_competencia=True).order_by("nome")
        if ups_id:
            if not ups_id.isdigit():
                raise ValidationError({"ups": "Informe uma UPS valida."})
            self._ups_estoque_cache = [
                get_object_or_404(participantes, pk=ups_id)
            ]
        else:
            self._ups_estoque_cache = list(participantes)
        return self._ups_estoque_cache

    def _dados_estoque_disponiveis(self):
        if hasattr(self, "_dados_estoque_disponiveis_cache"):
            return self._dados_estoque_disponiveis_cache
        competencia = self._competencia_estoque()
        if competencia is None:
            disponiveis = False
        else:
            ups_ids = [item.pk for item in self._ups_estoque()]
            ups_com_importacao = CompetenciaService.importacoes_validas(
                REPORT_TYPE_STOCK
            ).filter(
                competencia=competencia,
                ups_id__in=ups_ids,
            ).values("ups_id").distinct().count()
            # A consulta consolidada deve somar as UPS que possuem estoque
            # importado, sem zerar todo o resultado porque outra unidade ainda
            # não enviou seu relatório. Ao filtrar uma UPS específica, a mesma
            # regra naturalmente exige que ela possua uma importação válida.
            disponiveis = ups_com_importacao > 0
        self._dados_estoque_disponiveis_cache = disponiveis
        return disponiveis

    def _situacoes_validacao(self):
        if not hasattr(self, "_situacoes_validacao_cache"):
            self._situacoes_validacao_cache = (
                SituacaoValidacaoMedicamentosService.construir(
                    competencia=self._competencia_estoque(),
                    ups=self._ups_estoque(),
                )
            )
        return self._situacoes_validacao_cache

    def get_queryset(self):
        competencia = self._competencia_estoque()
        ups_selecionadas = self._ups_estoque()
        ups = ups_selecionadas[0] if self.request.query_params.get("ups") else None
        dados_disponiveis = self._dados_estoque_disponiveis()
        queryset = EstoqueTotalAdministrativoService.preparar_listagem(
            super().get_queryset(),
            competencia=competencia,
            ups=ups,
            dados_disponiveis=dados_disponiveis,
        )

        # A listagem administrativa representa o conteúdo efetivamente importado
        # no recorte selecionado, e não todo o cadastro histórico de medicamentos.
        # Assim, uma competência/UPS sem dados não exibe linhas artificiais zeradas.
        if self.action == "list":
            if competencia is None or not dados_disponiveis:
                return queryset.none()
            queryset = queryset.filter(
                saldos_estoque__competencia=competencia,
                saldos_estoque__ups_id__in=[item.pk for item in ups_selecionadas],
                saldos_estoque__importacao__tipo_relatorio=REPORT_TYPE_STOCK,
                saldos_estoque__importacao__status__in=(
                    CompetenciaService.STATUS_IMPORTACAO_VALIDOS
                ),
            ).distinct()

        unidade = self.request.query_params.get("unidade", "").strip()
        if unidade:
            queryset = queryset.filter(unidade__iexact=unidade)

        situacao = self.request.query_params.get("situacao", "").strip()
        if situacao == "disponivel":
            if not dados_disponiveis:
                return queryset.none()
            queryset = queryset.filter(quantidade_estoque_total__gt=0)
        elif situacao == "sem_estoque":
            if not dados_disponiveis:
                return queryset.none()
            queryset = queryset.filter(quantidade_estoque_total__lte=0)
        elif situacao == "sem_dados":
            queryset = queryset if not dados_disponiveis else queryset.none()
        elif situacao:
            raise ValidationError({"situacao": "Informe uma situacao valida."})

        validacao = self.request.query_params.get("validacao", "").strip()
        if validacao:
            if validacao not in {"validado", "divergente", "nao_validado"}:
                raise ValidationError(
                    {"validacao": "Informe uma situacao de validacao valida."}
                )
            ids = [
                medicamento_id
                for medicamento_id, estado in self._situacoes_validacao().items()
                if estado == validacao
            ]
            queryset = queryset.filter(pk__in=ids)

        ordenacao = self.request.query_params.get("ordenacao", "descricao")
        ordenacoes = {
            "descricao": ("descricao", "codigo_gmus"),
            "codigo": ("codigo_gmus", "descricao"),
            "maior_estoque": ("-quantidade_estoque_total", "descricao"),
            "menor_estoque": ("quantidade_estoque_total", "descricao"),
        }
        if ordenacao not in ordenacoes:
            raise ValidationError({"ordenacao": "Informe uma ordenacao valida."})
        return queryset.order_by(*ordenacoes[ordenacao])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            {
                "competencia_estoque": self._competencia_estoque(),
                "ups_estoque": self._ups_estoque(),
                "dados_estoque_disponiveis": self._dados_estoque_disponiveis(),
                "situacoes_validacao": self._situacoes_validacao(),
            }
        )
        return context

    @action(detail=False, methods=["get"], url_path="opcoes")
    def opcoes(self, request):
        competencia_padrao = EstoqueTotalAdministrativoService.competencia_padrao()
        competencias = CompetenciaService.competencias_ativas().order_by(
            "-ano", "-mes"
        )
        ups = Ups.objects.filter(
            participa_competencia=True,
            importacoes__tipo_relatorio=REPORT_TYPE_STOCK,
        ).distinct().order_by("nome")
        unidades = (
            Medicamento.objects.filter(
                saldos_estoque__importacao__tipo_relatorio=REPORT_TYPE_STOCK,
                saldos_estoque__importacao__status__in=(
                    CompetenciaService.STATUS_IMPORTACAO_VALIDOS
                ),
            )
            .exclude(unidade="")
            .exclude(unidade__isnull=True)
            .values_list("unidade", flat=True)
            .distinct()
            .order_by("unidade")
        )
        return Response(
            {
                "competencia_padrao_id": (
                    competencia_padrao.pk if competencia_padrao is not None else None
                ),
                "competencias": [
                    {"id": item.pk, "mes": item.mes, "ano": item.ano}
                    for item in competencias
                ],
                "ups": [
                    {
                        "id": item.pk,
                        "nome": item.nome,
                        "id_unidade_gmus": item.id_unidade_gmus,
                    }
                    for item in ups
                ],
                "unidades": list(unidades),
            }
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
        competencia = CompetenciaService.identificar_competencia_completa()
        if competencia is None:
            return Medicamento.objects.none()
        queryset = (
            Medicamento.objects.only("codigo_gmus", "descricao", "unidade")
            .filter(
                saldos_estoque__competencia=competencia,
                saldos_estoque__importacao__status__in=(
                    CompetenciaService.STATUS_IMPORTACAO_VALIDOS
                ),
            )
            .distinct()
        )
        return DisponibilidadePublicaService.anotar_disponibilidade(
            queryset,
            competencia=competencia,
        )
