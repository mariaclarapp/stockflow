import { ArrowRight, CircleSlash2, Layers3, PackageSearch, Pill, Tag } from "lucide-react";
import { Link } from "react-router-dom";

import { classificationStyle } from "./classificationPresentation";

function subgroupText(subgroup) {
  if (!subgroup) return "Não informado";
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Não informado");
}

function stockQuantityText(quantity) {
  if (quantity === null || quantity === undefined) return "Não informado";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}

function CategoryBadge({ children, filterValue, icon: Icon, onSelect, style, type }) {
  const className = `medication-category-badge medication-category-badge--${type}`;
  if (!filterValue || !onSelect) {
    return (
      <span className={className} style={style}>
        <Icon size={12} aria-hidden="true" />
        {children}
      </span>
    );
  }
  return (
    <button
      type="button"
      className={`${className} medication-category-badge--interactive`}
      style={style}
      onClick={() => onSelect(filterValue)}
      aria-label={`Filtrar por ${children}`}
      title={`Filtrar por ${children}`}
    >
      <Icon size={12} aria-hidden="true" />
      {children}
    </button>
  );
}

function MedicationDetails({ medication, onCategorySelect }) {
  const principles = medication.principios_ativos || [];
  const classifications = medication.classificacoes || [];
  const manipulated = classifications.filter(
    (item) => item.nome?.toUpperCase() === "MANIPULADO",
  );
  const manualCategories = classifications.filter(
    (item) => item.nome?.toUpperCase() !== "MANIPULADO",
  );
  const hasOfficialCategory = Boolean(medication.subgrupo_gmus);

  return (
    <div className="medication-details">
      <span className="medication-category-badges">
        {hasOfficialCategory ? (
          <CategoryBadge
            filterValue={`subgrupo:${medication.subgrupo_gmus.id}`}
            icon={Layers3}
            onSelect={onCategorySelect}
            type="subgroup"
          >
            {subgroupText(medication.subgrupo_gmus)}
          </CategoryBadge>
        ) : manualCategories.length ? (
          manualCategories.map((classification) => (
            <CategoryBadge
              key={classification.id}
              filterValue={classification.ativo
                ? `classificacao:${classification.id}`
                : ""}
              icon={Tag}
              onSelect={onCategorySelect}
              style={classificationStyle(classification.cor)}
              type="manual"
            >
              {classification.nome}
            </CategoryBadge>
          ))
        ) : (
          <CategoryBadge icon={CircleSlash2} type="unclassified">
            Não classificado
          </CategoryBadge>
        )}

        {manipulated.map((classification) => (
          <CategoryBadge
            key={classification.id}
            filterValue={classification.ativo
              ? `classificacao:${classification.id}`
              : ""}
            icon={Tag}
            onSelect={onCategorySelect}
            style={classificationStyle(classification.cor)}
            type="manipulated"
          >
            {classification.nome}
          </CategoryBadge>
        ))}
      </span>
      {principles.length > 0 && (
        <span className="medication-principles">
          {principles.map((principle) => principle.nome).join(", ")}
        </span>
      )}
    </div>
  );
}

function MedicationList({ medications, onCategorySelect }) {
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
              <th scope="col">Medicamento / Categoria</th>
              <th scope="col">Unidade</th>
              <th scope="col">Estoque total</th>
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
                  <MedicationDetails
                    medication={medication}
                    onCategorySelect={onCategorySelect}
                  />
                </td>
                <td>{medication.unidade || "Não informada"}</td>
                <td className="medication-stock-quantity">
                  {stockQuantityText(medication.quantidade_estoque_total)}
                </td>
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
            <MedicationDetails
              medication={medication}
              onCategorySelect={onCategorySelect}
            />
            <dl>
              <div>
                <dt>Estoque total</dt>
                <dd className="medication-stock-quantity">
                  {stockQuantityText(medication.quantidade_estoque_total)}
                </dd>
              </div>
            </dl>
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
