import {
  AlertCircle,
  BarChart3,
  Check,
  Layers3,
  LoaderCircle,
  Pill,
  RefreshCw,
  SearchCheck,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { getDashboardSummary } from "../api/dashboard";
import ImportStatusBadge from "../components/imports/ImportStatusBadge";
import { formatCompetence } from "../utils/formatters";

function requestErrorMessage(error) {
  if (error instanceof ApiError && error.status === 0) {
    return "A API está temporariamente indisponível. Tente novamente.";
  }
  return "Não foi possível carregar o resumo administrativo.";
}

function formatDateTime(value) {
  if (!value) return "Não informada";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Não informada";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [requestVersion, setRequestVersion] = useState(0);
  const [selectedAlert, setSelectedAlert] = useState(null);

  const loadSummary = useCallback(() => {
    setIsLoading(true);
    setError("");
    setSummary(null);
    setRequestVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    let isCurrent = true;

    getDashboardSummary()
      .then((data) => {
        if (isCurrent) setSummary(data);
      })
      .catch((requestError) => {
        if (!isCurrent) return;
        setSummary(null);
        setError(requestErrorMessage(requestError));
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [requestVersion]);

  const competence = summary?.competencia_atual || null;
  const importedUps = summary?.ups.importadas || 0;
  const participatingUps = summary?.ups.participantes || 0;
  const progress = participatingUps
    ? Math.min((importedUps / participatingUps) * 100, 100)
    : 0;
  const overviewCards = useMemo(
    () => [
      {
        label: "Medicamentos na competência",
        value: summary?.totais.medicamentos ?? "--",
        detail: competence ? "Apresentações importadas" : "Sem dados importados",
        icon: Pill,
      },
      {
        label: "Registros da competência",
        value: competence ? summary.totais.estoques : "--",
        detail: competence ? formatCompetence(competence) : "Sem competência importada",
        icon: Layers3,
      },
      {
        label: "UPS importadas",
        value: summary ? `${importedUps}/${participatingUps}` : "--",
        detail: "Unidades participantes",
        icon: Check,
      },
    ],
    [competence, importedUps, participatingUps, summary],
  );

  return (
    <main className="dashboard-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Administrativo</span>
          <h1>Visão geral</h1>
          <p>Acompanhe a competência mensal e as importações de estoque.</p>
        </div>
      </header>

      {error && (
        <div
          className="request-feedback request-feedback--error dashboard-error"
          role="alert"
        >
          <AlertCircle size={18} />
          <p>{error}</p>
          <button type="button" onClick={loadSummary}>
            <RefreshCw size={15} />
            Tentar novamente
          </button>
        </div>
      )}

      <section className="competence-banner" aria-labelledby="competence-title">
        <div>
          <span>{competence?.completa ? "Competência completa" : competence ? "Competência em andamento" : "Resumo mensal"}</span>
          <h2 id="competence-title">
            {isLoading
              ? "Carregando resumo..."
              : competence
                ? formatCompetence(competence)
                : "Nenhuma competência importada"}
          </h2>
          <p>
            {competence
              ? `${importedUps} de ${participatingUps} UPS participantes com estoque válido.${competence.completa ? " Competência pronta para consolidação." : " Ainda existem UPS pendentes."}`
              : "Ainda não há importações de estoque válidas para acompanhar."}
          </p>
        </div>
        <div className="competence-progress" aria-hidden="true">
          <span style={{ width: `${isLoading ? 0 : progress}%` }} />
        </div>
      </section>

      <nav className="dashboard-quick-actions" aria-label="Atalhos administrativos">
        <Link to="/admin/importacoes"><Upload size={18} /><span><strong>Importar relatórios</strong><small>Estoque e movimentações</small></span></Link>
        <Link to="/admin/validacao"><SearchCheck size={18} /><span><strong>Validar competência</strong><small>Conferir saldo mensal</small></span></Link>
        <Link to="/admin/analises"><BarChart3 size={18} /><span><strong>Abrir análises</strong><small>Consumo, média e cobertura</small></span></Link>
      </nav>

      <section className="overview-grid" aria-label="Resumo da competência">
        {overviewCards.map(({ label, value, detail, icon: Icon }) => (
          <article className="overview-card" key={label}>
            <span className="overview-card__icon" aria-hidden="true">
              <Icon size={18} />
            </span>
            <span>
              <small>{label}</small>
              <strong>{isLoading ? "--" : value}</strong>
              <p>{isLoading ? "Carregando dados" : detail}</p>
            </span>
          </article>
        ))}
      </section>

      <section className="imports-panel" aria-labelledby="imports-title">
        <div className="section-heading">
          <div>
            <h2 id="imports-title">Situação das importações</h2>
            <p>Resumo por UPS da competência importada mais recente.</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>UPS</th>
                <th>Status</th>
                <th>Registros</th>
                <th>Importado em</th>
                <th>Responsável</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan="5">
                    <div className="empty-table-state">
                      <LoaderCircle className="button-spinner" size={22} />
                      <strong>Carregando importações</strong>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading &&
                summary?.importacoes.map((item) => (
                  <tr key={item.ups.id}>
                    <td>
                      <span className="dashboard-ups-cell">
                        <strong>{item.ups.nome}</strong>
                        <small>
                          Unidade G-MUS {item.ups.id_unidade_gmus}
                        </small>
                      </span>
                    </td>
                    <td>
                      {item.pendencias_abertas > 0 ? (
                        <button
                          className="dashboard-status-link"
                          type="button"
                          onClick={() => setSelectedAlert(item)}
                          aria-label={`Ver alerta da importação da ${item.ups.nome}`}
                        >
                          <ImportStatusBadge status={item.status} />
                        </button>
                      ) : (
                        <ImportStatusBadge status="concluida" />
                      )}
                    </td>
                    <td>{item.registros_estoque}</td>
                    <td>{formatDateTime(item.data_importacao)}</td>
                    <td>{item.usuario || "Não informado"}</td>
                  </tr>
                ))}
              {!isLoading && !error && summary?.importacoes.length === 0 && (
                <tr>
                  <td colSpan="5">
                    <div className="empty-table-state">
                      <Layers3 size={22} aria-hidden="true" />
                      <strong>Nenhuma importação de estoque disponível</strong>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selectedAlert && (
        <div className="confirmation-overlay" role="presentation" onClick={() => setSelectedAlert(null)}>
          <section
            className="confirmation-dialog dashboard-alert-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dashboard-alert-title"
            onClick={(event) => event.stopPropagation()}
          >
            <span className="confirmation-dialog__icon confirmation-dialog__icon--warning" aria-hidden="true">
              <AlertCircle size={22} />
            </span>
            <div className="confirmation-dialog__content">
              <h2 id="dashboard-alert-title">Atenção na importação</h2>
              <p>
                A importação de <strong>{selectedAlert.ups.nome}</strong> precisa de revisão:
                {selectedAlert.alertas_relevantes > 0 && ` ${selectedAlert.alertas_relevantes} alerta(s) não bloqueante(s)`}
                {selectedAlert.alertas_relevantes > 0 && selectedAlert.erros_nao_corrigiveis > 0 ? " e" : ""}
                {selectedAlert.erros_nao_corrigiveis > 0 && ` ${selectedAlert.erros_nao_corrigiveis} linha(s) rejeitada(s)`}.
              </p>
              <p>
                Consulte o histórico para ver as pendências corrigíveis. Para alertas ou linhas rejeitadas, corrija o relatório no G-MUS e reimporte-o.
              </p>
            </div>
            <div className="confirmation-dialog__actions">
              <button className="secondary-button" type="button" onClick={() => setSelectedAlert(null)}>
                Fechar
              </button>
              <Link className="primary-button" to={`/admin/importacoes?importacao=${selectedAlert.importacao_id || ""}`} onClick={() => setSelectedAlert(null)}>
                Ver importação
              </Link>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default DashboardPage;
