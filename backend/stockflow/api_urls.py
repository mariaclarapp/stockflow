from django.urls import path
from rest_framework.routers import DefaultRouter

from core.auth_views import (
    CsrfCookieAPIView,
    CurrentUserAPIView,
    LoginAPIView,
    LogoutAPIView,
)
from core.views import CompetenciaViewSet, DashboardResumoAPIView, UpsViewSet
from estoques.views import HistoricoMedicamentoAPIView, EstoqueViewSet, LoteViewSet
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
    path("auth/csrf/", CsrfCookieAPIView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="auth-logout"),
    path("auth/me/", CurrentUserAPIView.as_view(), name="auth-me"),
    path(
        "dashboard/resumo/",
        DashboardResumoAPIView.as_view(),
        name="dashboard-resumo",
    ),
    path(
        "publico/medicamentos/",
        MedicamentoPublicoListAPIView.as_view(),
        name="public-medicamento-list",
    ),
    path(
        "medicamentos/<int:pk>/historico/",
        HistoricoMedicamentoAPIView.as_view(),
        name="medicamento-historico",
    ),
    path(
        "importacoes/inventario/",
        InventoryUploadAPIView.as_view(),
        name="inventory-import-upload",
    ),
] + router.urls
