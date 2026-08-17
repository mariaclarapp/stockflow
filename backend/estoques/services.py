from collections import OrderedDict
from decimal import Decimal

from core.services import CompetenciaService

from .models import Estoque


class HistoricoMedicamentoService:
    @classmethod
    def construir(cls, medicamento_id):
        competencias_completas = list(
            CompetenciaService.competencias_completas()
            .order_by("-ano", "-mes")
            .values("id", "ano", "mes")
        )
        ids_completas = {item["id"] for item in competencias_completas}
        competencia_atual = competencias_completas[0] if competencias_completas else None

        estoques = (
            Estoque.objects.filter(medicamento_id=medicamento_id)
            .select_related("competencia", "ups", "lote")
            .order_by(
                "-competencia__ano",
                "-competencia__mes",
                "ups__nome",
                "ups_id",
                "id",
            )
        )
        grupos = cls._agrupar_estoques(estoques, ids_completas)

        estoque_atual = None
        if competencia_atual is not None:
            grupo_atual = grupos.pop(competencia_atual["id"], None)
            estoque_atual = cls._estoque_atual(
                grupo_atual,
                competencia_atual,
            )

        return {
            "medicamento_id": medicamento_id,
            "estoque_atual": estoque_atual,
            "historico": [cls._resumo_historico(grupo) for grupo in grupos.values()],
        }

    @staticmethod
    def _agrupar_estoques(estoques, ids_completas):
        grupos = OrderedDict()
        for estoque in estoques:
            competencia = estoque.competencia
            grupo = grupos.setdefault(
                competencia.pk,
                {
                    "competencia": {
                        "id": competencia.pk,
                        "ano": competencia.ano,
                        "mes": competencia.mes,
                        "completa": competencia.pk in ids_completas,
                    },
                    "quantidade_consolidada_convencional": Decimal("0.000"),
                    "por_ups": OrderedDict(),
                },
            )
            ups = estoque.ups
            grupo_ups = grupo["por_ups"].setdefault(
                ups.pk,
                {
                    "ups": {
                        "id": ups.pk,
                        "codigo_gmus": ups.codigo_gmus,
                        "id_unidade_gmus": ups.id_unidade_gmus,
                        "nome": ups.nome,
                        "compoe_estoque_convencional": (
                            ups.compoe_estoque_convencional
                        ),
                    },
                    "quantidade_total": Decimal("0.000"),
                    "registros": [],
                },
            )
            grupo_ups["quantidade_total"] += estoque.quantidade
            grupo_ups["registros"].append(
                {
                    "estoque_id": estoque.pk,
                    "quantidade": estoque.quantidade,
                    "lote": (
                        {
                            "id": estoque.lote.pk,
                            "codigo_lote": estoque.lote.codigo_lote,
                            "data_validade": estoque.lote.data_validade,
                        }
                        if estoque.lote
                        else None
                    ),
                }
            )
            if ups.compoe_estoque_convencional:
                grupo["quantidade_consolidada_convencional"] += estoque.quantidade
        return grupos

    @staticmethod
    def _estoque_atual(grupo, competencia):
        if grupo is None:
            return {
                "competencia": {**competencia, "completa": True},
                "quantidade_consolidada_convencional": Decimal("0.000"),
                "por_ups": [],
            }
        return {
            "competencia": grupo["competencia"],
            "quantidade_consolidada_convencional": grupo[
                "quantidade_consolidada_convencional"
            ],
            "por_ups": list(grupo["por_ups"].values()),
        }

    @staticmethod
    def _resumo_historico(grupo):
        return {
            "competencia": grupo["competencia"],
            "quantidade_consolidada_convencional": grupo[
                "quantidade_consolidada_convencional"
            ],
            "por_ups": [
                {
                    "ups": {
                        "id": item["ups"]["id"],
                        "codigo_gmus": item["ups"]["codigo_gmus"],
                        "id_unidade_gmus": item["ups"]["id_unidade_gmus"],
                        "nome": item["ups"]["nome"],
                    },
                    "quantidade_total": item["quantidade_total"],
                }
                for item in grupo["por_ups"].values()
            ],
        }
