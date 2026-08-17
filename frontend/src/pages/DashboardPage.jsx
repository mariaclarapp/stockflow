import { Check, FileText, Layers3 } from "lucide-react";

const overviewCards = [
  { label: "UPS importadas", icon: Check },
  { label: "Registros do mês", icon: Layers3 },
  { label: "Importações", icon: FileText },
];

function DashboardPage() {
  return (
    <main className="dashboard-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Administrativo</span>
          <h1>Visão geral</h1>
          <p>Acompanhe a competência mensal e as importações de estoque.</p>
        </div>
        <span className="placeholder-badge">Estrutura inicial</span>
      </header>

      <section className="competence-banner" aria-labelledby="competence-title">
        <div>
          <span>Competência completa</span>
          <h2 id="competence-title">Sem dados disponíveis</h2>
          <p>A situação será exibida após a integração do dashboard.</p>
        </div>
        <div className="competence-progress" aria-hidden="true">
          <span />
        </div>
      </section>

      <section className="overview-grid" aria-label="Resumo da competência">
        {overviewCards.map(({ label, icon: Icon }) => (
          <article className="overview-card" key={label}>
            <span className="overview-card__icon" aria-hidden="true">
              <Icon size={18} />
            </span>
            <span>
              <small>{label}</small>
              <strong>--</strong>
              <p>Aguardando dados</p>
            </span>
          </article>
        ))}
      </section>

      <section className="imports-panel" aria-labelledby="imports-title">
        <div className="section-heading">
          <div>
            <h2 id="imports-title">Situação das importações</h2>
            <p>Resumo por UPS da competência selecionada.</p>
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
              <tr>
                <td colSpan="4">
                  <div className="empty-table-state">
                    <Layers3 size={22} aria-hidden="true" />
                    <strong>Dados ainda não disponíveis</strong>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default DashboardPage;
