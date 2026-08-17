from django.db.models import Count, Q

from estoques.models import Estoque
from importacoes.models import Importacao
from medicamentos.models import Medicamento

from .models import Competencia, Ups


class CompetenciaService:
    TIPO_RELATORIO_INVENTARIO = "inventario"
    STATUS_IMPORTACAO_VALIDOS = (
        Importacao.Status.CONCLUIDA,
        Importacao.Status.CONCLUIDA_COM_ALERTAS,
    )

    @classmethod
    def competencias_completas(cls, total_ups_participantes=None):
        if total_ups_participantes is None:
            total_ups_participantes = Ups.objects.filter(
                participa_competencia=True
            ).count()
        if total_ups_participantes == 0:
            return Competencia.objects.none()

        return Competencia.objects.annotate(
            total_ups_importadas=Count(
                "importacoes__ups",
                filter=Q(
                    importacoes__tipo_relatorio=cls.TIPO_RELATORIO_INVENTARIO,
                    importacoes__status__in=cls.STATUS_IMPORTACAO_VALIDOS,
                    importacoes__ups__participa_competencia=True,
                ),
                distinct=True,
            )
        ).filter(total_ups_importadas=total_ups_participantes)

    @classmethod
    def identificar_competencia_completa(cls, total_ups_participantes=None):
        return cls.competencias_completas(
            total_ups_participantes=total_ups_participantes
        ).order_by("-ano", "-mes").first()


class DashboardResumoService:
    @classmethod
    def construir(cls):
        total_ups_participantes = Ups.objects.filter(
            participa_competencia=True
        ).count()
        competencia = CompetenciaService.identificar_competencia_completa(
            total_ups_participantes=total_ups_participantes
        )
        total_medicamentos = Medicamento.objects.count()

        if competencia is None:
            return {
                "competencia_atual": None,
                "ups": {
                    "participantes": total_ups_participantes,
                    "importadas": 0,
                },
                "importacoes": [],
                "totais": {
                    "medicamentos": total_medicamentos,
                    "estoques": 0,
                },
            }

        importacoes = list(
            Importacao.objects.filter(
                competencia=competencia,
                tipo_relatorio=CompetenciaService.TIPO_RELATORIO_INVENTARIO,
                ups__participa_competencia=True,
            )
            .select_related("ups")
            .annotate(registros_estoque=Count("estoques"))
            .order_by("ups__nome", "ups_id")
        )
        status_validos = CompetenciaService.STATUS_IMPORTACAO_VALIDOS

        return {
            "competencia_atual": {
                "id": competencia.pk,
                "ano": competencia.ano,
                "mes": competencia.mes,
                "completa": True,
            },
            "ups": {
                "participantes": total_ups_participantes,
                "importadas": sum(
                    importacao.status in status_validos
                    for importacao in importacoes
                ),
            },
            "importacoes": [
                {
                    "ups": {
                        "id": importacao.ups_id,
                        "codigo_gmus": importacao.ups.codigo_gmus,
                        "id_unidade_gmus": importacao.ups.id_unidade_gmus,
                        "nome": importacao.ups.nome,
                    },
                    "status": importacao.status,
                    "data_importacao": importacao.data_importacao,
                    "registros_estoque": importacao.registros_estoque,
                }
                for importacao in importacoes
            ],
            "totais": {
                "medicamentos": total_medicamentos,
                "estoques": Estoque.objects.filter(
                    competencia=competencia
                ).count(),
            },
        }
