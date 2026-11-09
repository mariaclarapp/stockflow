from django.urls import path
from rest_framework.routers import DefaultRouter

from core.auth_views import (
    CsrfCookieAPIView,
    CurrentUserAPIView,
    FuncionarioListCreateAPIView,
    FuncionarioDetailAPIView,
    LoginAPIView,
    LogoutAPIView,
    PasswordChangeAPIView,
)
from core.views import (
    CompetenciaViewSet,
    CompetenciasAcompanhamentoAPIView,
    DashboardResumoAPIView,
    UpsViewSet,
)
from estoques.views import (
    AnaliseConsumoAPIView,
    HistoricoMedicamentoAPIView,
    EstoqueViewSet,
    SaldoEstoqueViewSet,
    ValidacaoMovimentacoesAPIView,
)
from importacoes.views import (
    ImportacaoDeleteAPIView,
    ImportacaoPendenciaResolveAPIView,
    ImportPreviewAPIView,
    ImportacaoViewSet,
    MovementUploadAPIView,
    MovimentacaoEstoqueViewSet,
    StockUploadAPIView,
)
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
router.register("estoques", EstoqueViewSet, basename="estoque")
router.register("saldos-estoque", SaldoEstoqueViewSet, basename="saldo-estoque")
router.register("movimentacoes", MovimentacaoEstoqueViewSet, basename="movimentacao")
router.register("importacoes", ImportacaoViewSet, basename="importacao")

urlpatterns = [
    path("auth/csrf/", CsrfCookieAPIView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="auth-logout"),
    path("auth/me/", CurrentUserAPIView.as_view(), name="auth-me"),
    path("auth/password/", PasswordChangeAPIView.as_view(), name="auth-password"),
    path(
        "usuarios/funcionarios/",
        FuncionarioListCreateAPIView.as_view(),
        name="funcionario-list-create",
    ),
    path(
        "usuarios/funcionarios/<int:pk>/",
        FuncionarioDetailAPIView.as_view(),
        name="funcionario-detail",
    ),
    path(
        "dashboard/resumo/",
        DashboardResumoAPIView.as_view(),
        name="dashboard-resumo",
    ),
    path(
        "competencias/acompanhamento/",
        CompetenciasAcompanhamentoAPIView.as_view(),
        name="competencias-acompanhamento",
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
        "analises/consumo/",
        AnaliseConsumoAPIView.as_view(),
        name="analise-consumo",
    ),
    path(
        "estoques/validacao-movimentacoes/",
        ValidacaoMovimentacoesAPIView.as_view(),
        name="estoque-validacao-movimentacoes",
    ),
    path(
        "importacoes/previsualizar/",
        ImportPreviewAPIView.as_view(),
        name="importacao-preview",
    ),
    path(
        "importacoes/estoque/",
        StockUploadAPIView.as_view(),
        name="stock-import-upload",
    ),
    path(
        "importacoes/movimentacoes/",
        MovementUploadAPIView.as_view(),
        name="movement-import-upload",
    ),
    path(
        "importacoes/<int:pk>/pendencias/<int:pendencia_id>/resolver/",
        ImportacaoPendenciaResolveAPIView.as_view(),
        name="importacao-pendencia-resolver",
    ),
    path(
        "importacoes/<int:pk>/",
        ImportacaoDeleteAPIView.as_view(),
        name="importacao-delete",
    ),
] + router.urls
