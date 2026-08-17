import { PackageSearch } from "lucide-react";

import AvailabilityBadge from "./AvailabilityBadge";

function PublicMedicationResults({ medications, searchTerm }) {
  return (
    <section className="public-results" aria-labelledby="public-results-title">
      <div className="public-results__heading">
        <div>
          <span>Resultado da consulta</span>
          <h2 id="public-results-title">Medicamentos encontrados</h2>
        </div>
        <p>
          {medications.length} {medications.length === 1 ? "apresentação" : "apresentações"}
          {` para “${searchTerm}”`}
        </p>
      </div>

      <div className="public-results__grid">
        {medications.map((medication) => (
          <article className="public-medication-card" key={medication.codigo_gmus}>
            <header>
              <span className="public-medication-card__icon" aria-hidden="true">
                <PackageSearch size={19} />
              </span>
              <span className="public-medication-card__code">
                Código G-MUS {medication.codigo_gmus}
              </span>
            </header>
            <h3>{medication.descricao}</h3>
            <div className="public-medication-card__footer">
              <span className="public-medication-card__unit">
                Unidade <strong>{medication.unidade}</strong>
              </span>
              <AvailabilityBadge status={medication.disponibilidade} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default PublicMedicationResults;
