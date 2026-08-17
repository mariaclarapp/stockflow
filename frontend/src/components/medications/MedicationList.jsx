import { ArrowRight, PackageSearch, Pill } from "lucide-react";
import { Link } from "react-router-dom";

function subgroupText(subgroup) {
  if (!subgroup) return "Não informado";
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Não informado");
}

function MedicationDetails({ medication }) {
  const principles = medication.principios_ativos || [];
  const classifications = medication.classificacoes || [];

  if (!principles.length && !classifications.length) return null;

  return (
    <div className="medication-details">
      {principles.length > 0 && (
        <span className="medication-principles">
          {principles.map((principle) => principle.nome).join(", ")}
        </span>
      )}
      {classifications.length > 0 && (
        <span className="medication-classifications">
          {classifications.map((classification) => (
            <span
              key={classification.id}
              className="medication-classification"
              style={classification.cor ? { borderColor: classification.cor } : undefined}
            >
              {classification.nome}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

function MedicationList({ medications }) {
  if (!medications.length) {
    return (
      <div className="medication-empty-state">
        <span aria-hidden="true">
          <PackageSearch size={27} />
        </span>
        <div>
          <strong>Nenhum medicamento encontrado</strong>
          <p>Nenhum medicamento corresponde aos filtros informados.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="medication-table-wrapper">
        <table className="medication-table">
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Medicamento / Apresentação</th>
              <th scope="col">Unidade</th>
              <th scope="col">Subgrupo G-MUS</th>
              <th scope="col"><span className="visually-hidden">Ação</span></th>
            </tr>
          </thead>
          <tbody>
            {medications.map((medication) => (
              <tr key={medication.id}>
                <td>
                  <span className="gmus-code">{medication.codigo_gmus}</span>
                </td>
                <td>
                  <strong className="medication-name">{medication.descricao}</strong>
                  <MedicationDetails medication={medication} />
                </td>
                <td>{medication.unidade || "Não informada"}</td>
                <td>{subgroupText(medication.subgrupo_gmus)}</td>
                <td className="medication-table__action">
                  <Link
                    className="medication-detail-link"
                    to={`/admin/medicamentos/${medication.id}`}
                    aria-label={`Ver detalhes de ${medication.descricao}`}
                  >
                    Ver detalhes
                    <ArrowRight size={15} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="medication-card-list">
        {medications.map((medication) => (
          <article className="medication-card" key={medication.id}>
            <header>
              <span className="medication-card__icon" aria-hidden="true">
                <Pill size={18} />
              </span>
              <span className="gmus-code">{medication.codigo_gmus}</span>
              <span className="medication-unit">{medication.unidade || "Sem unidade"}</span>
            </header>
            <h3>{medication.descricao}</h3>
            <dl>
              <div>
                <dt>Subgrupo G-MUS</dt>
                <dd>{subgroupText(medication.subgrupo_gmus)}</dd>
              </div>
            </dl>
            <MedicationDetails medication={medication} />
            <Link
              className="medication-card__detail-link"
              to={`/admin/medicamentos/${medication.id}`}
            >
              Ver detalhes
              <ArrowRight size={15} />
            </Link>
          </article>
        ))}
      </div>
    </>
  );
}

export default MedicationList;
