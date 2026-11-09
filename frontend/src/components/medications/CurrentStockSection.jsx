import { Boxes, CalendarCheck2, CircleCheck, MapPin, PackageOpen } from "lucide-react";

import { formatCompetence, formatDecimal } from "../../utils/formatters";

function Quantity({ value, unit }) {
  return (
    <>
      {formatDecimal(value)}
      {unit && <small> {unit}</small>}
    </>
  );
}

function CurrentStockSection({ stock, totalQuantity, unit }) {
  if (!stock) {
    return (
      <section className="detail-section" aria-labelledby="current-stock-title">
        <div className="detail-section__heading">
          <div>
            <span className="eyebrow">Posição consolidada</span>
            <h2 id="current-stock-title">Estoque atual</h2>
          </div>
        </div>
        <div className="detail-empty-state">
          <CalendarCheck2 size={27} aria-hidden="true" />
          <div>
            <strong>
              Nenhuma competência completa disponível para determinar o estoque atual.
            </strong>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="detail-section" aria-labelledby="current-stock-title">
      <div className="detail-section__heading current-stock-heading">
        <div>
          <span className="eyebrow">Posição consolidada</span>
          <h2 id="current-stock-title">Estoque atual</h2>
          <p>Competência {formatCompetence(stock.competencia)}</p>
        </div>
        <span className="competence-status competence-status--complete">
          <CircleCheck size={15} />
          Competência completa
        </span>
      </div>

      <div className="current-stock-total">
        <span aria-hidden="true"><Boxes size={23} /></span>
        <div>
          <small>Estoque total administrativo</small>
          <strong><Quantity value={totalQuantity} unit={unit} /></strong>
        </div>
      </div>

      {stock.por_ups.length === 0 ? (
        <div className="current-stock-empty">
          <PackageOpen size={21} />
          <p>O medicamento não possui registros nesta competência completa.</p>
        </div>
      ) : (
        <div className="ups-stock-grid">
          {stock.por_ups.map((item) => (
            <article className="ups-stock-card" key={item.ups.id}>
              <header>
                <span className="ups-stock-card__icon" aria-hidden="true">
                  <MapPin size={18} />
                </span>
                <div>
                  <h3>{item.ups.nome}</h3>
                  <p>
                    Unidade G-MUS {item.ups.id_unidade_gmus}
                  </p>
                </div>
                <span className={`consolidation-badge${item.ups.compoe_estoque_convencional ? "" : " consolidation-badge--excluded"}`}>
                  {item.ups.compoe_estoque_convencional
                    ? "Compõe o convencional"
                    : "Fora do convencional"}
                </span>
              </header>

              <div className="ups-stock-card__total">
                <small>Quantidade total na UPS</small>
                <strong><Quantity value={item.quantidade_total} unit={unit} /></strong>
              </div>

            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default CurrentStockSection;
