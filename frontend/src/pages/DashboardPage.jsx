import {
  AlertCircle,
  Check,
  FileText,
  Layers3,
  LoaderCircle,
  Pill,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

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
        label: "Medicamentos cadastrados",
        value: summary?.totais.medicamentos ?? "--",
        detail: "Apresentações no StockFlow",
        icon: Pill,
      },
      {
        label: "Registros da competência",
        value: competence ? summary.totais.estoques : "--",
        detail: competence
          ? formatCompetence(competence)
          : "Sem competência completa",
        icon: Layers3,
      },
      {
        label: "UPS importadas",
        value: summary ? `${importedUps}/${participatingUps}` : "--",
        detail: "Unidades participantes",
        icon: Check,
      },
      {
        label: "Importações válidas",
        value: summary?.importacoes.length ?? "--",
        detail: competence
          ? "Inventários da competência"
          : "Sem competência completa",
        icon: FileText,
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
          <span>{competence ? "Competência completa" : "Resumo mensal"}</span>
          <h2 id="competence-title">
            {isLoading
              ? "Carregando resumo..."
              : competence
                ? formatCompetence(competence)
                : "Nenhuma competência completa"}
          </h2>
          <p>
            {competence
              ? `${importedUps} de ${participatingUps} UPS participantes com inventário válido.`
              : "Ainda não há uma competência com todas as importações participantes válidas."}
          </p>
        </div>
        <div className="competence-progress" aria-hidden="true">
          <span style={{ width: `${isLoading ? 0 : progress}%` }} />
        </div>
      </section>

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
            <p>Resumo por UPS da competência completa mais recente.</p>
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
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan="4">
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
                      <ImportStatusBadge status={item.status} />
                    </td>
                    <td>{item.registros_estoque}</td>
                    <td>{formatDateTime(item.data_importacao)}</td>
                  </tr>
                ))}
              {!isLoading && !error && summary?.importacoes.length === 0 && (
                <tr>
                  <td colSpan="4">
                    <div className="empty-table-state">
                      <Layers3 size={22} aria-hidden="true" />
                      <strong>Nenhuma competência completa disponível</strong>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default DashboardPage;
