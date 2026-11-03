import {
  Boxes,
  CalendarDays,
  FileCheck2,
  Pill,
  RotateCcw,
  Warehouse,
} from "lucide-react";

import ImportStatusBadge from "./ImportStatusBadge";
import IssuesList from "./IssuesList";
import PendingImportResolutions from "./PendingImportResolutions";

function formatCompetence(competence) {
  if (!competence) return "Não informada";
  return `${String(competence.mes).padStart(2, "0")}/${competence.ano}`;
}

function reportTypeLabel(reportType) {
  if (reportType === "inventario") return "Inventário";
  if (reportType === "estoque") return "Consulta de Estoque";
  if (reportType === "movimentacao") return "Movimentações de Estoque";
  return reportType;
}

function ImportSummary({ result, fileName, onDelete, onImportUpdated, isDeleting }) {
  const stats = [
    { label: "Processados", value: result.registros_processados, icon: FileCheck2 },
    { label: "Ignorados", value: result.registros_ignorados, icon: Boxes },
    { label: "Medicamentos criados", value: result.medicamentos_criados, icon: Pill },
    {
      label: "Medicamentos reutilizados",
      value: result.medicamentos_reutilizados,
      icon: RotateCcw,
    },
    { label: "Estoques criados", value: result.estoques_criados, icon: Warehouse },
    ...(result.quantidade_nao_associada
      ? [{
          label: "Quantidade sem código",
          value: result.quantidade_nao_associada,
          icon: Boxes,
        }]
      : []),
  ];

  return (
    <section className="import-result" aria-labelledby="import-result-title">
      <header className="import-result__header">
        <div>
          <span className="eyebrow">
            {result.reimportacao ? "Estoque substituído" : "Resultado do processamento"}
          </span>
          <h2 id="import-result-title">
            {result.reimportacao ? "Reimportação concluída" : "Importação registrada"}
          </h2>
        </div>
        <ImportStatusBadge status={result.status} />
      </header>

      <div className="import-context">
        <div>
          <CalendarDays size={17} aria-hidden="true" />
          <span>
            <small>Competência</small>
            <strong>{formatCompetence(result.competencia)}</strong>
          </span>
        </div>
        <div>
          <Warehouse size={17} aria-hidden="true" />
          <span>
            <small>UPS</small>
            <strong>{result.ups?.nome || "Não informada"}</strong>
            {result.ups?.id_unidade_gmus && (
              <em>Unidade G-MUS {result.ups.id_unidade_gmus}</em>
            )}
          </span>
        </div>
        <div>
          <FileCheck2 size={17} aria-hidden="true" />
          <span>
            <small>Relatório</small>
            <strong>{reportTypeLabel(result.tipo_relatorio)}</strong>
            <em>{fileName}</em>
          </span>
        </div>
      </div>

      <div className="import-stats">
        {stats.map(({ label, value, icon: Icon }) => (
          <article key={label}>
            <Icon size={17} aria-hidden="true" />
            <span>
              <strong>{value}</strong>
              <small>{label}</small>
            </span>
          </article>
        ))}
      </div>

      <div className="issues-grid">
        <PendingImportResolutions
          importId={result.importacao_id}
          pendencias={result.pendencias}
          onResolved={onImportUpdated}
        />
        <IssuesList kind="divergences" issues={result.divergencias} />
        <IssuesList kind="warnings" issues={result.warnings} />
        <IssuesList kind="errors" issues={result.erros} />
      </div>

      <div className="import-result__actions">
        <button className="secondary-button secondary-button--danger" type="button" onClick={onDelete} disabled={isDeleting}>
          {isDeleting ? "Excluindo..." : "Excluir esta importação"}
        </button>
      </div>
    </section>
  );
}

export default ImportSummary;
