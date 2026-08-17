import { CalendarClock, CircleAlert, CircleCheck, History } from "lucide-react";

import { formatCompetence, formatDecimal } from "../../utils/formatters";

function Quantity({ value, unit }) {
  return `${formatDecimal(value)}${unit ? ` ${unit}` : ""}`;
}

function UpsTotals({ items, unit }) {
  if (!items.length) return <span className="history-no-ups">Sem registros por UPS</span>;
  return (
    <ul className="history-ups-list">
      {items.map((item) => (
        <li key={item.ups.id}>
          <span>{item.ups.nome}</span>
          <strong><Quantity value={item.quantidade_total} unit={unit} /></strong>
        </li>
      ))}
    </ul>
  );
}

function HistorySection({ history, unit }) {
  return (
    <section className="detail-section" aria-labelledby="history-title">
      <div className="detail-section__heading">
        <div>
          <span className="eyebrow">Evolução mensal</span>
          <h2 id="history-title">Histórico de estoque</h2>
          <p>Competências com registros anteriores ou incompletos.</p>
        </div>
      </div>

      {history.length === 0 ? (
        <div className="detail-empty-state">
          <History size={27} aria-hidden="true" />
          <div>
            <strong>Histórico ainda não disponível</strong>
            <p>Não existem outras competências com estoque para este medicamento.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th scope="col">Competência</th>
                  <th scope="col">Situação</th>
                  <th scope="col">Consolidado convencional</th>
                  <th scope="col">Totais por UPS</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.competencia.id}>
                    <td>
                      <span className="history-competence">
                        <CalendarClock size={16} />
                        {formatCompetence(item.competencia)}
                      </span>
                    </td>
                    <td>
                      <span className={`competence-status${item.competencia.completa ? " competence-status--complete" : " competence-status--incomplete"}`}>
                        {item.competencia.completa
                          ? <CircleCheck size={14} />
                          : <CircleAlert size={14} />}
                        {item.competencia.completa ? "Completa" : "Incompleta"}
                      </span>
                    </td>
                    <td className="history-total">
                      <Quantity value={item.quantidade_consolidada_convencional} unit={unit} />
                    </td>
                    <td><UpsTotals items={item.por_ups} unit={unit} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="history-card-list">
            {history.map((item) => (
              <article className="history-card" key={item.competencia.id}>
                <header>
                  <strong>{formatCompetence(item.competencia)}</strong>
                  <span className={`competence-status${item.competencia.completa ? " competence-status--complete" : " competence-status--incomplete"}`}>
                    {item.competencia.completa ? "Completa" : "Incompleta"}
                  </span>
                </header>
                <div className="history-card__total">
                  <small>Consolidado convencional</small>
                  <strong><Quantity value={item.quantidade_consolidada_convencional} unit={unit} /></strong>
                </div>
                <UpsTotals items={item.por_ups} unit={unit} />
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default HistorySection;
