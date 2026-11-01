from django.db.models import Count, Q

from estoques.models import SaldoEstoque
from importacoes.models import Importacao
from importacoes.report_types import REPORT_TYPE_MOVEMENT, REPORT_TYPE_STOCK
from medicamentos.models import Medicamento

from .models import Competencia, Ups


class CompetenciaService:
    TIPOS_RELATORIO_ESTOQUE = (REPORT_TYPE_STOCK,)
    TIPOS_RELATORIO_ATIVOS = (REPORT_TYPE_STOCK, REPORT_TYPE_MOVEMENT)
    STATUS_IMPORTACAO_VALIDOS = (
        Importacao.Status.CONCLUIDA,
        Importacao.Status.CONCLUIDA_COM_ALERTAS,
    )
    STATUS_IMPORTACAO_DISPONIVEIS = STATUS_IMPORTACAO_VALIDOS

    @classmethod
    def importacoes_validas(cls, tipo_relatorio):
        """Return only imports that are safe to use in official calculations."""
        return Importacao.objects.filter(
            tipo_relatorio=tipo_relatorio,
            status__in=cls.STATUS_IMPORTACAO_VALIDOS,
        )

    @classmethod
    def competencias_ativas(cls):
        """Competences backed by at least one import from the active workflow."""
        return Competencia.objects.filter(
            importacoes__tipo_relatorio__in=cls.TIPOS_RELATORIO_ATIVOS
        ).distinct()

    @classmethod
    def importacao_valida(cls, *, competencia, ups, tipo_relatorio):
        return (
            cls.importacoes_validas(tipo_relatorio)
            .filter(competencia=competencia, ups=ups)
            .first()
        )

    @classmethod
    def importacao_anterior_valida(cls, *, competencia, ups, tipo_relatorio):
        return (
            cls.importacoes_validas(tipo_relatorio)
            .filter(
                Q(competencia__ano__lt=competencia.ano)
                | Q(
                    competencia__ano=competencia.ano,
                    competencia__mes__lt=competencia.mes,
                ),
                ups=ups,
            )
            .select_related("competencia", "ups")
            .order_by("-competencia__ano", "-competencia__mes")
            .first()
        )

    @classmethod
    def competencias_com_totais(cls):
        return cls.competencias_ativas().annotate(
            total_ups_importadas=Count(
                "importacoes__ups",
                filter=Q(
                    importacoes__tipo_relatorio__in=cls.TIPOS_RELATORIO_ESTOQUE,
                    importacoes__status__in=cls.STATUS_IMPORTACAO_VALIDOS,
                    importacoes__ups__participa_competencia=True,
                ),
                distinct=True,
            )
        )

    @classmethod
    def competencias_completas(cls, total_ups_participantes=None):
        if total_ups_participantes is None:
            total_ups_participantes = Ups.objects.filter(
                participa_competencia=True
            ).count()
        if total_ups_participantes == 0:
            return Competencia.objects.none()

        return cls.competencias_com_totais().filter(
            total_ups_importadas=total_ups_participantes
        )

    @classmethod
    def identificar_competencia_completa(cls, total_ups_participantes=None):
        return cls.competencias_completas(
            total_ups_participantes=total_ups_participantes
        ).order_by("-ano", "-mes").first()

    @classmethod
    def identificar_competencia_disponivel(cls):
        return (
            cls.competencias_com_totais()
            .filter(
                importacoes__tipo_relatorio__in=cls.TIPOS_RELATORIO_ESTOQUE,
                importacoes__status__in=cls.STATUS_IMPORTACAO_DISPONIVEIS,
            )
            .order_by("-ano", "-mes")
            .first()
        )


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
                tipo_relatorio__in=CompetenciaService.TIPOS_RELATORIO_ESTOQUE,
                ups__participa_competencia=True,
            )
            .select_related("ups")
            .annotate(
                registros_estoque=Count("saldos_estoque")
            )
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
                "estoques": SaldoEstoque.objects.filter(
                    competencia=competencia
                ).count(),
            },
        }


class CompetenciasAcompanhamentoService:
    @classmethod
    def construir(cls):
        ups_participantes = list(
            Ups.objects.filter(participa_competencia=True).order_by("nome", "id")
        )
        total_esperadas = len(ups_participantes)
        competencias = list(
            CompetenciaService.competencias_com_totais().order_by("-ano", "-mes")
        )
        competencia_ids = [competencia.pk for competencia in competencias]

        importacoes_por_chave = {}
        if competencia_ids:
            importacoes = (
                Importacao.objects.filter(
                    competencia_id__in=competencia_ids,
                    tipo_relatorio__in=CompetenciaService.TIPOS_RELATORIO_ESTOQUE,
                    ups__participa_competencia=True,
                )
                .select_related("ups")
                .annotate(
                    registros_estoque=Count("saldos_estoque")
                )
            )
            for importacao in importacoes:
                chave = (importacao.competencia_id, importacao.ups_id)
                importacoes_por_chave[chave] = importacao

        resultado = []
        competencia_completa_mais_recente = None
        for competencia in competencias:
            completa = (
                total_esperadas > 0
                and competencia.total_ups_importadas == total_esperadas
            )
            if completa and competencia_completa_mais_recente is None:
                competencia_completa_mais_recente = {
                    "id": competencia.pk,
                    "ano": competencia.ano,
                    "mes": competencia.mes,
                }

            situacoes = []
            for ups in ups_participantes:
                importacao = importacoes_por_chave.get((competencia.pk, ups.pk))
                situacoes.append(
                    {
                        "id": ups.pk,
                        "codigo_gmus": ups.codigo_gmus,
                        "id_unidade_gmus": ups.id_unidade_gmus,
                        "nome": ups.nome,
                        "importada": importacao is not None,
                        "status": importacao.status if importacao else None,
                        "data_importacao": (
                            importacao.data_importacao if importacao else None
                        ),
                        "registros_estoque": (
                            importacao.registros_estoque if importacao else None
                        ),
                    }
                )

            resultado.append(
                {
                    "id": competencia.pk,
                    "ano": competencia.ano,
                    "mes": competencia.mes,
                    "completa": completa,
                    "ups": {
                        "esperadas": total_esperadas,
                        "importadas_validas": competencia.total_ups_importadas,
                        "situacoes": situacoes,
                    },
                }
            )

        return {
            "competencia_completa_mais_recente": competencia_completa_mais_recente,
            "competencias": resultado,
        }
