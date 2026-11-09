import csv
import logging

from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .parsers import UnknownReportTypeError, parse_report_csv
from .models import Importacao, MovimentacaoEstoque, PendenciaImportacao
from .serializers import (
    ImportacaoSerializer,
    InventoryUploadSerializer,
    PendenciaImportacaoSerializer,
    ResolverPendenciaImportacaoSerializer,
)
from .serializers import MovimentacaoEstoqueSerializer
from .services import (
    InventoryImportConflictError,
    InventoryPersistenceError,
    persist_movement_import,
    persist_stock_import,
    delete_importacao,
    find_existing_import,
    resolver_pendencia_importacao,
)


logger = logging.getLogger(__name__)


class MovimentacaoEstoqueViewSet(ReadOnlyModelViewSet):
    queryset = MovimentacaoEstoque.objects.select_related(
        "medicamento", "ups", "competencia", "importacao"
    )
    serializer_class = MovimentacaoEstoqueSerializer
    permission_classes = [IsAdminUser]


class ImportacaoViewSet(ReadOnlyModelViewSet):
    queryset = Importacao.objects.filter(
        tipo_relatorio__in=("estoque", "movimentacao")
    ).select_related("competencia", "ups", "usuario").prefetch_related(
        Prefetch(
            "pendencias",
            queryset=PendenciaImportacao.objects.filter(
                status=PendenciaImportacao.Status.PENDENTE
            ).select_related("medicamento"),
            to_attr="pendencias_abertas_prefetch",
        )
    )
    serializer_class = ImportacaoSerializer
    permission_classes = [IsAdminUser]


class ImportacaoDeleteAPIView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        if request.data.get("confirmar") is not True:
            return Response(
                {"erro": "Confirme explicitamente a exclusao da importacao."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        get_object_or_404(Importacao, pk=pk)
        result = delete_importacao(importacao_id=pk, deleted_by=request.user)
        return Response({"importacao_id": pk, **result}, status=status.HTTP_200_OK)


class ImportacaoPendenciaResolveAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk, pendencia_id):
        get_object_or_404(Importacao, pk=pk)
        get_object_or_404(PendenciaImportacao, pk=pendencia_id, importacao_id=pk)
        serializer = ResolverPendenciaImportacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resultado = resolver_pendencia_importacao(
                importacao_id=pk,
                pendencia_id=pendencia_id,
                codigo_gmus=serializer.validated_data["codigo_gmus"],
                resolvida_por=request.user,
            )
        except InventoryPersistenceError as error:
            return Response({"erro": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        importacao = (
            Importacao.objects.select_related("competencia", "ups", "usuario")
            .prefetch_related(
                Prefetch(
                    "pendencias",
                    queryset=PendenciaImportacao.objects.filter(
                        status=PendenciaImportacao.Status.PENDENTE
                    ).select_related("medicamento"),
                    to_attr="pendencias_abertas_prefetch",
                )
            )
            .get(pk=pk)
        )
        return Response(
            {
                "importacao": ImportacaoSerializer(importacao).data,
                "pendencia": PendenciaImportacaoSerializer(
                    resultado["pendencia"]
                ).data,
                "medicamento_criado": resultado["medicamento_criado"],
                "saldo_criado": resultado["saldo_criado"],
                "saldo": str(resultado["saldo"].quantidade),
            }
        )


class ImportPreviewAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InventoryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data["arquivo"]
        try:
            parsed_data = parse_report_csv(arquivo)
        except UnknownReportTypeError as error:
            return Response(
                {"erro": str(error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except (csv.Error, UnicodeError, ValueError):
            return Response(
                {"erro": "Nao foi possivel interpretar o arquivo CSV."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metadata = parsed_data.get("metadata", {})
        issues = parsed_data.get("inconsistencies", [])
        errors = [item for item in issues if item.get("severity", "error") == "error"]
        warnings = [item for item in issues if item.get("severity") == "warning"]
        existing_import = find_existing_import(parsed_data)
        return Response(
            {
                "tipo_relatorio": parsed_data.get("tipo_relatorio"),
                "competencia": metadata.get("competencia"),
                "ups": metadata.get("ups"),
                "data_inicial": metadata.get("data_inicial"),
                "data_final": metadata.get("data_final"),
                "registros_identificados": len(parsed_data.get("records", [])),
                "erros": [_serialize_issue(item) for item in errors],
                "warnings": [_serialize_issue(item) for item in warnings],
                "pode_importar": not any(item.get("line") is None for item in errors)
                and bool(parsed_data.get("records")),
                "importacao_existente": existing_import is not None,
                "importacao_id": existing_import.pk if existing_import else None,
                "mesmo_arquivo": bool(
                    existing_import
                    and existing_import.hash_arquivo == parsed_data.get("hash_arquivo")
                ),
            }
        )


class ReportUploadAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]


class StockUploadAPIView(ReportUploadAPIView):
    def post(self, request):
        serializer = InventoryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data["arquivo"]
        reimportar = serializer.validated_data["reimportar"]

        try:
            parsed_data = parse_report_csv(arquivo)
        except UnknownReportTypeError as error:
            return Response(
                {"erro": str(error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except (csv.Error, UnicodeError, ValueError):
            return Response(
                {"erro": "Nao foi possivel interpretar o arquivo CSV."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if parsed_data.get("tipo_relatorio") != "estoque":
            return Response(
                {"erro": "Envie um relatorio de Consulta de Estoque."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        blocking_errors = [
            item
            for item in parsed_data.get("inconsistencies", [])
            if item.get("severity", "error") == "error" and item.get("line") is None
        ]
        if blocking_errors or not parsed_data.get("records"):
            return Response(
                {
                    "erro": "O arquivo nao possui registros processaveis.",
                    "inconsistencias": [_serialize_issue(item) for item in blocking_errors],
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            summary = persist_stock_import(
                parsed_data=parsed_data,
                user=request.user,
                nome_arquivo=arquivo.name,
                reimportar=reimportar,
            )
        except InventoryImportConflictError as error:
            return Response({"erro": str(error)}, status=status.HTTP_409_CONFLICT)
        except InventoryPersistenceError as error:
            return Response({"erro": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Falha inesperada ao persistir estoque.")
            return Response(
                {"erro": "Ocorreu um erro inesperado ao processar a importacao."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            _build_success_response(summary),
            status=status.HTTP_200_OK if summary["reimportacao"] else status.HTTP_201_CREATED,
        )


class MovementUploadAPIView(ReportUploadAPIView):
    def post(self, request):
        serializer = InventoryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data["arquivo"]
        reimportar = serializer.validated_data["reimportar"]
        try:
            parsed_data = parse_report_csv(arquivo)
        except UnknownReportTypeError as error:
            return Response({"erro": str(error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except (csv.Error, UnicodeError, ValueError):
            return Response({"erro": "Nao foi possivel interpretar o arquivo CSV."}, status=status.HTTP_400_BAD_REQUEST)
        if parsed_data.get("tipo_relatorio") != "movimentacao":
            return Response({"erro": "Envie um relatorio de movimentacao sintetica."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        blocking_errors = [item for item in parsed_data.get("inconsistencies", []) if item.get("severity", "error") == "error" and item.get("line") is None]
        if blocking_errors or not parsed_data.get("records"):
            return Response({"erro": "O arquivo nao possui registros processaveis.", "inconsistencias": [_serialize_issue(item) for item in blocking_errors]}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        try:
            summary = persist_movement_import(parsed_data=parsed_data, user=request.user, nome_arquivo=arquivo.name, reimportar=reimportar)
        except InventoryImportConflictError as error:
            return Response({"erro": str(error)}, status=status.HTTP_409_CONFLICT)
        except InventoryPersistenceError as error:
            return Response({"erro": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Falha inesperada ao persistir movimentacoes.")
            return Response({"erro": "Ocorreu um erro inesperado ao processar a importacao."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(_build_success_response(summary), status=status.HTTP_200_OK if summary["reimportacao"] else status.HTTP_201_CREATED)


def _build_success_response(summary):
    importacao = summary["importacao"]
    issues = summary.get("erros", [])
    return {
        "importacao_id": importacao.pk,
        "reimportacao": summary["reimportacao"],
        "status": importacao.status,
        "tipo_relatorio": importacao.tipo_relatorio,
        "hash_arquivo": importacao.hash_arquivo,
        "competencia": {
            "ano": importacao.competencia.ano,
            "mes": importacao.competencia.mes,
        },
        "ups": {
            "codigo_gmus": importacao.ups.codigo_gmus,
            "id_unidade_gmus": importacao.ups.id_unidade_gmus,
            "nome": importacao.ups.nome,
        },
        "registros_processados": summary["registros_processados"],
        "registros_ignorados": summary["registros_ignorados"],
        "medicamentos_criados": summary["medicamentos_criados"],
        "medicamentos_reutilizados": summary["medicamentos_reutilizados"],
        "lotes_criados": summary["lotes_criados"],
        "lotes_reutilizados": summary["lotes_reutilizados"],
        "estoques_criados": summary["estoques_criados"],
        "quantidade_nao_associada": summary.get(
            "quantidade_nao_associada", importacao.quantidade_nao_associada
        ),
        "pendencias": PendenciaImportacaoSerializer(
            importacao.pendencias.filter(
                status=PendenciaImportacao.Status.PENDENTE
            ).select_related("medicamento"),
            many=True,
        ).data,
        "divergencias": [
            _serialize_issue(item) for item in summary.get("divergencias", [])
        ],
        "warnings": [
            _serialize_issue(item)
            for item in issues
            if item.get("severity") == "warning"
        ],
        "erros": [
            _serialize_issue(item)
            for item in issues
            if item.get("severity", "error") == "error"
        ],
    }


def _serialize_issue(issue):
    allowed_fields = (
        "line",
        "type",
        "tipo",
        "severity",
        "message",
        "codigo_gmus",
        "valor_cadastrado",
        "valor_relatorio",
    )
    return {field: issue[field] for field in allowed_fields if field in issue}
