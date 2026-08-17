import csv
import logging

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .parsers import parse_inventory_csv
from .serializers import InventoryUploadSerializer
from .services import (
    DuplicateInventoryImportError,
    InventoryPersistenceError,
    persist_inventory_import,
)


logger = logging.getLogger(__name__)


class InventoryUploadAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InventoryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data["arquivo"]

        try:
            parsed_data = parse_inventory_csv(arquivo)
        except (csv.Error, UnicodeError, ValueError):
            return Response(
                {"erro": "Nao foi possivel interpretar o arquivo CSV."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blocking_errors = [
            item
            for item in parsed_data.get("inconsistencies", [])
            if item.get("severity", "error") == "error"
            and item.get("line") is None
        ]
        if blocking_errors or not parsed_data.get("records"):
            return Response(
                {
                    "erro": "O arquivo nao possui registros processaveis.",
                    "inconsistencias": [
                        _serialize_issue(item) for item in blocking_errors
                    ],
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            summary = persist_inventory_import(
                parsed_data=parsed_data,
                user=request.user,
                nome_arquivo=arquivo.name,
            )
        except DuplicateInventoryImportError as error:
            return Response(
                {"erro": str(error)},
                status=status.HTTP_409_CONFLICT,
            )
        except InventoryPersistenceError as error:
            return Response(
                {"erro": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Falha inesperada ao persistir inventario.")
            return Response(
                {"erro": "Ocorreu um erro inesperado ao processar a importacao."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            _build_success_response(summary),
            status=status.HTTP_201_CREATED,
        )


def _build_success_response(summary):
    importacao = summary["importacao"]
    issues = summary.get("erros", [])
    return {
        "importacao_id": importacao.pk,
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
