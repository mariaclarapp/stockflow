import { AlertCircle, AlertTriangle, GitCompareArrows } from "lucide-react";

const issueTypeLabels = {
  medicamento_descricao: "Descrição do medicamento divergente",
  medicamento_unidade: "Unidade do medicamento divergente",
  medicamento_subgrupo: "Subgrupo do medicamento divergente",
  subgrupo_nome: "Nome do subgrupo divergente",
  negative_quantity: "Quantidade de estoque negativa",
  persistence_validation: "Registro não persistido",
};

const listConfig = {
  divergences: {
    title: "Divergências",
    icon: GitCompareArrows,
    tone: "neutral",
  },
  warnings: { title: "Alertas", icon: AlertTriangle, tone: "warning" },
  errors: { title: "Linhas rejeitadas", icon: AlertCircle, tone: "danger" },
};

function issueTitle(issue) {
  return (
    issue.message ||
    issueTypeLabels[issue.tipo || issue.type] ||
    "Ocorrência identificada durante o processamento"
  );
}

function IssuesList({ kind, issues }) {
  if (!issues?.length) return null;
  const config = listConfig[kind];
  const Icon = config.icon;

  return (
    <section className={`issues-panel issues-panel--${config.tone}`}>
      <header>
        <Icon size={18} />
        <h3>{config.title}</h3>
        <span>{issues.length}</span>
      </header>
      <ul>
        {issues.map((issue, index) => (
          <li key={`${issue.line || "global"}-${issue.tipo || issue.type}-${index}`}>
            <div>
              <strong>{issueTitle(issue)}</strong>
              {(issue.line || issue.codigo_gmus) && (
                <small>
                  {issue.line ? `Linha ${issue.line}` : ""}
                  {issue.line && issue.codigo_gmus ? " · " : ""}
                  {issue.codigo_gmus ? `Código ${issue.codigo_gmus}` : ""}
                </small>
              )}
            </div>
            {(issue.valor_cadastrado !== undefined ||
              issue.valor_relatorio !== undefined) && (
              <dl>
                <div>
                  <dt>Cadastrado</dt>
                  <dd>{String(issue.valor_cadastrado ?? "Não informado")}</dd>
                </div>
                <div>
                  <dt>Relatório</dt>
                  <dd>{String(issue.valor_relatorio ?? "Não informado")}</dd>
                </div>
              </dl>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default IssuesList;
