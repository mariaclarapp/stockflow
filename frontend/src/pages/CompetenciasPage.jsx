import {
  AlertCircle,
  CalendarCheck2,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleDashed,
  FileUp,
  LoaderCircle,
  ListFilter,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { getCompetenciesTracking } from "../api/competencies";
import FilterSelect from "../components/filters/FilterSelect";
import ImportStatusBadge from "../components/imports/ImportStatusBadge";
import { formatCompetence } from "../utils/formatters";

const STATUS_OPTIONS = [
  { value: "completa", label: "Completa" },
  { value: "incompleta", label: "Incompleta" },
];

function requestErrorMessage(error) {
  if (error instanceof ApiError && error.status === 0) {
    return "A API está temporariamente indisponível. Tente novamente.";
  }
  return "Não foi possível carregar o acompanhamento das competências.";
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function CompetenciasPage() {
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [requestVersion, setRequestVersion] = useState(0);
  const [yearFilter, setYearFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  const loadTracking = useCallback(() => {
    setIsLoading(true);
    setError("");
    setTracking(null);
    setRequestVersion((version) => version + 1);
  }, []);

  useEffect(() => {
    let isCurrent = true;

    getCompetenciesTracking()
      .then((data) => {
        if (isCurrent) setTracking(data);
      })
      .catch((requestError) => {
        if (!isCurrent) return;
        setTracking(null);
        setError(requestErrorMessage(requestError));
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [requestVersion]);

  const competencies = useMemo(
    () => tracking?.competencias ?? [],
    [tracking],
  );
  const years = useMemo(
    () => [...new Set(competencies.map((item) => item.ano))],
    [competencies],
  );
  const yearOptions = useMemo(
    () => years.map((year) => ({ value: String(year), label: String(year) })),
    [years],
  );
  const filteredCompetencies = useMemo(
    () =>
      competencies.filter((item) => {
        const matchesYear = !yearFilter || String(item.ano) === yearFilter;
        const matchesStatus =
          !statusFilter ||
          (statusFilter === "completa" ? item.completa : !item.completa);
        return matchesYear && matchesStatus;
      }),
    [competencies, statusFilter, yearFilter],
  );
  const completeCount = competencies.filter((item) => item.completa).length;

  function toggleCompetence(id) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <main className="competencies-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Acompanhamento mensal</span>
          <h1>Competências</h1>
          <p>Confira a situação dos inventários esperados em cada UPS.</p>
        </div>
      </header>

      {error && (
        <div className="request-feedback request-feedback--error dashboard-error" role="alert">
          <AlertCircle size={18} />
          <p>{error}</p>
          <button type="button" onClick={loadTracking}>
            <RefreshCw size={15} />
            Tentar novamente
          </button>
        </div>
      )}

      <section className="competencies-summary" aria-label="Resumo das competências">
        <div>
          <span className="competencies-summary__icon"><CalendarCheck2 size={18} /></span>
          <small>Mais recente completa</small>
          <strong>
            {tracking?.competencia_completa_mais_recente
              ? formatCompetence(tracking.competencia_completa_mais_recente)
              : "Não disponível"}
          </strong>
        </div>
        <div>
          <span className="competencies-summary__icon"><CalendarCheck2 size={18} /></span>
          <small>Competências completas</small>
          <strong>{isLoading ? "--" : completeCount}</strong>
        </div>
        <div>
          <span className="competencies-summary__icon"><CircleDashed size={18} /></span>
          <small>Em acompanhamento</small>
          <strong>{isLoading ? "--" : competencies.length - completeCount}</strong>
        </div>
      </section>

      <section className="competencies-panel" aria-labelledby="competencies-list-title">
        <div className="competencies-toolbar">
          <div>
            <h2 id="competencies-list-title">Histórico de competências</h2>
            <p>Abra uma competência para consultar cada UPS participante.</p>
          </div>
          <div className="competencies-filters">
            <FilterSelect
              id="competence-year"
              label="Ano"
              value={yearFilter}
              options={yearOptions}
              placeholder="Todos"
              icon={CalendarDays}
              onChange={setYearFilter}
            />
            <FilterSelect
              id="competence-status"
              label="Situação"
              value={statusFilter}
              options={STATUS_OPTIONS}
              placeholder="Todas"
              icon={ListFilter}
              onChange={setStatusFilter}
            />
          </div>
        </div>

        {isLoading && (
          <div className="competencies-state">
            <LoaderCircle className="button-spinner" size={24} />
            <strong>Carregando competências</strong>
          </div>
        )}

        {!isLoading && !error && competencies.length === 0 && (
          <div className="competencies-state">
            <CalendarCheck2 size={24} />
            <strong>Nenhuma competência cadastrada</strong>
            <p>As competências aparecerão após as importações de inventário.</p>
            <Link className="secondary-button" to="/admin/importacoes">
              <FileUp size={16} /> Ir para importações
            </Link>
          </div>
        )}

        {!isLoading && !error && competencies.length > 0 && filteredCompetencies.length === 0 && (
          <div className="competencies-state">
            <CircleDashed size={24} />
            <strong>Nenhuma competência corresponde aos filtros</strong>
          </div>
        )}

        {!isLoading && filteredCompetencies.length > 0 && (
          <div className="competencies-list">
            {filteredCompetencies.map((competence) => {
              const isExpanded = expandedIds.has(competence.id);
              const isLatestComplete =
                competence.id === tracking?.competencia_completa_mais_recente?.id;
              const progress = competence.ups.esperadas
                ? (competence.ups.importadas_validas / competence.ups.esperadas) * 100
                : 0;

              return (
                <article className="competence-item" key={competence.id}>
                  <button
                    type="button"
                    className="competence-item__toggle"
                    onClick={() => toggleCompetence(competence.id)}
                    aria-expanded={isExpanded}
                  >
                    <span className="competence-item__chevron" aria-hidden="true">
                      {isExpanded ? <ChevronDown size={19} /> : <ChevronRight size={19} />}
                    </span>
                    <span className="competence-item__identity">
                      <strong>{formatCompetence(competence)}</strong>
                      {isLatestComplete && <small>Completa mais recente</small>}
                    </span>
                    <span className={`competence-status competence-status--${competence.completa ? "complete" : "incomplete"}`}>
                      {competence.completa ? "Completa" : "Incompleta"}
                    </span>
                    <span className="competence-item__progress-label">
                      {competence.ups.importadas_validas} de {competence.ups.esperadas} UPS válidas
                    </span>
                  </button>
                  <div className="competence-item__progress" aria-hidden="true">
                    <span style={{ width: `${Math.min(progress, 100)}%` }} />
                  </div>

                  {isExpanded && (
                    <div className="competence-item__details">
                      <div className="table-wrapper">
                        <table>
                          <thead>
                            <tr>
                              <th>UPS participante</th>
                              <th>Situação</th>
                              <th>Registros</th>
                              <th>Importado em</th>
                            </tr>
                          </thead>
                          <tbody>
                            {competence.ups.situacoes.map((ups) => (
                              <tr key={ups.id}>
                                <td>
                                  <span className="dashboard-ups-cell">
                                    <strong>{ups.nome}</strong>
                                    <small>Unidade G-MUS {ups.id_unidade_gmus}</small>
                                  </span>
                                </td>
                                <td>
                                  {ups.importada ? (
                                    <ImportStatusBadge status={ups.status} />
                                  ) : (
                                    <span className="status-badge status-badge--pending">
                                      <CircleDashed size={15} /> Importação pendente
                                    </span>
                                  )}
                                </td>
                                <td>{ups.registros_estoque ?? "--"}</td>
                                <td>{formatDateTime(ups.data_importacao)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {!competence.completa && (
                        <div className="competence-item__action">
                          <span>Complete os inventários pendentes desta competência.</span>
                          <Link className="secondary-button" to="/admin/importacoes">
                            <FileUp size={16} /> Ir para importações
                          </Link>
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}

export default CompetenciasPage;
