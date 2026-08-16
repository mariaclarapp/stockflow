from django.urls import path
from rest_framework.routers import DefaultRouter

from core.views import CompetenciaViewSet, UpsViewSet
from estoques.views import EstoqueViewSet, LoteViewSet
from importacoes.views import InventoryUploadAPIView
from medicamentos.views import (
    ClassificacaoViewSet,
    MedicamentoViewSet,
    MedicamentoPublicoListAPIView,
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

urlpatterns = [
    path(
        "publico/medicamentos/",
        MedicamentoPublicoListAPIView.as_view(),
        name="public-medicamento-list",
    ),
    path(
        "importacoes/inventario/",
        InventoryUploadAPIView.as_view(),
        name="inventory-import-upload",
    ),
] + router.urls
