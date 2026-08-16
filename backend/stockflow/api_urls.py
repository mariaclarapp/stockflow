from rest_framework.routers import DefaultRouter

from core.views import CompetenciaViewSet, UpsViewSet
from estoques.views import EstoqueViewSet, LoteViewSet
from medicamentos.views import (
    ClassificacaoViewSet,
    MedicamentoViewSet,
    PrincipioAtivoViewSet,
    SubgrupoGmusViewSet,
)


router = DefaultRouter()
router.register("subgrupos-gmus", SubgrupoGmusViewSet, basename="subgrupo-gmus")
router.register("principios-ativos", PrincipioAtivoViewSet, basename="principio-ativo")
router.register("classificacoes", ClassificacaoViewSet, basename="classificacao")
router.register("medicamentos", MedicamentoViewSet, basename="medicamento")
router.register("ups", UpsViewSet, basename="ups")
router.register("competencias", CompetenciaViewSet, basename="competencia")
router.register("lotes", LoteViewSet, basename="lote")
router.register("estoques", EstoqueViewSet, basename="estoque")

urlpatterns = router.urls
