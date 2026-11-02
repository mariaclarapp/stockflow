import {
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  CircleSlash2,
  Clock3,
  Layers3,
  MapPin,
  PackageSearch,
  Pill,
  Tag,
} from "lucide-react";
import { Link } from "react-router-dom";

import { classificationStyle } from "./classificationPresentation";
import { stockQuantityText } from "./medicationPresentation";

function subgroupText(subgroup) {
  if (!subgroup) return "Não informado";
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Não informado");
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

export function MedicationCategoryBadges({ medication, onCategorySelect }) {
  const classifications = medication.classificacoes || [];
  const manipulated = classifications.filter(
    (item) => item.nome?.toUpperCase() === "MANIPULADO",
  );
  const manualCategories = classifications.filter(
    (item) => item.nome?.toUpperCase() !== "MANIPULADO",
  );
  const hasOfficialCategory = Boolean(medication.subgrupo_gmus);

  return (
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
            filterValue={classification.ativo ? `classificacao:${classification.id}` : ""}
            icon={Tag}
            onSelect={onCategorySelect}
            style={classificationStyle(classification.cor)}
            type="manual"
          >
            {classification.nome}
          </CategoryBadge>
        ))
      ) : (
        <CategoryBadge
          filterValue="sem_categoria"
          icon={CircleSlash2}
          onSelect={onCategorySelect}
          type="unclassified"
        >
          Não classificado
        </CategoryBadge>
      )}

      {manipulated.map((classification) => (
        <CategoryBadge
          key={classification.id}
          filterValue={classification.ativo ? `classificacao:${classification.id}` : ""}
          icon={Tag}
          onSelect={onCategorySelect}
          style={classificationStyle(classification.cor)}
          type="manipulated"
        >
          {classification.nome}
        </CategoryBadge>
      ))}
    </span>
  );
}

function MedicationDetails({ medication, onCategorySelect }) {
  const principles = medication.principios_ativos || [];
  return (
    <div className="medication-details">
      <MedicationCategoryBadges medication={medication} onCategorySelect={onCategorySelect} />
      {principles.length > 0 && (
        <span className="medication-principles">
          {principles.map((principle) => principle.nome).join(", ")}
        </span>
      )}
    </div>
  );
}

function StockStatus({ status }) {
  const [modifier, Icon, label] = {
    disponivel: ["available", CheckCircle2, "Com estoque"],
    sem_estoque: ["empty", CircleSlash2, "Sem estoque"],
    sem_dados: ["unknown", CircleHelp, "Sem dados"],
  }[status] || ["unknown", CircleHelp, "Sem dados"];

  return (
    <span className={`medication-stock-status medication-stock-status--${modifier}`}>
      <Icon size={13} aria-hidden="true" />
      {label}
    </span>
  );
}

function ValidationStatus({ status }) {
  const [modifier, Icon, label] = {
    validado: ["validated", CheckCircle2, "Validado"],
    divergente: ["divergent", AlertTriangle, "Divergente"],
    nao_validado: ["pending", Clock3, "Não validado"],
  }[status] || ["pending", Clock3, "Não validado"];

  return (
    <span className={`medication-validation-status medication-validation-status--${modifier}`}>
      <Icon size={13} aria-hidden="true" />
      {label}
    </span>
  );
}

function StockByUps({ items }) {
  if (!items?.length) {
    return <span className="medication-ups-empty">Sem dados por UPS</span>;
  }
  return (
    <span className="medication-ups-stock">
      {items.map((item) => (
        <span className="medication-ups-stock__item" key={item.ups_id}>
          <MapPin size={11} aria-hidden="true" />
          <span className="medication-ups-stock__identity" title={item.ups_nome}>
            <b>{item.ups_nome}</b>
            {item.id_unidade_gmus && (
              <small>Unidade G-MUS {item.id_unidade_gmus}</small>
            )}
          </span>
          <strong>{stockQuantityText(item.quantidade)}</strong>
        </span>
      ))}
    </span>
  );
}

function MedicationList({
  medications,
  selectedUpsId,
  selectedUpsName,
  onCategorySelect,
}) {
  if (!medications.length) {
    return (
      <div className="medication-empty-state">
        <span aria-hidden="true"><PackageSearch size={27} /></span>
        <div>
          <strong>Nenhum medicamento encontrado</strong>
          <p>Não há medicamentos importados para esta competência e UPS, ou nenhum item corresponde aos filtros informados.</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="medication-table-wrapper">
        <table className={`medication-table${selectedUpsId ? " medication-table--single-ups" : ""}`}>
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Medicamento / Categoria</th>
              <th scope="col">Unidade</th>
              <th scope="col">{selectedUpsId ? "Estoque na UPS" : "Estoque total"}</th>
              <th scope="col">Por UPS</th>
              <th scope="col">Situação</th>
              <th scope="col"><span className="visually-hidden">Ação</span></th>
            </tr>
          </thead>
          <tbody>
            {medications.map((medication) => (
              <tr key={medication.id}>
                <td><span className="gmus-code">{medication.codigo_gmus}</span></td>
                <td>
                  <strong className="medication-name">{medication.descricao}</strong>
                  <MedicationDetails medication={medication} onCategorySelect={onCategorySelect} />
                </td>
                <td>{medication.unidade || "Não informada"}</td>
                <td className="medication-stock-quantity">
                  {stockQuantityText(medication.quantidade_estoque_total)}
                  {selectedUpsId && selectedUpsName && (
                    <small className="medication-stock-origin">{selectedUpsName}</small>
                  )}
                </td>
                <td>
                  <StockByUps items={medication.estoque_por_ups} selectedUpsId={selectedUpsId} />
                </td>
                <td>
                  <span className="medication-indicators">
                    <StockStatus status={medication.situacao_estoque} />
                    <ValidationStatus status={medication.situacao_validacao} />
                  </span>
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
              <span className="medication-card__icon" aria-hidden="true"><Pill size={18} /></span>
              <span className="gmus-code">{medication.codigo_gmus}</span>
              <span className="medication-unit">{medication.unidade || "Sem unidade"}</span>
            </header>
            <h3>{medication.descricao}</h3>
            <MedicationDetails medication={medication} onCategorySelect={onCategorySelect} />
            <dl>
              <div>
                <dt>{selectedUpsId ? "Estoque na UPS" : "Estoque total"}</dt>
                <dd className="medication-stock-quantity">
                  {stockQuantityText(medication.quantidade_estoque_total)}
                </dd>
              </div>
              <div>
                <dt>Situação</dt>
                <dd className="medication-indicators">
                  <StockStatus status={medication.situacao_estoque} />
                  <ValidationStatus status={medication.situacao_validacao} />
                </dd>
              </div>
            </dl>
            <StockByUps items={medication.estoque_por_ups} selectedUpsId={selectedUpsId} />
            <Link className="medication-card__detail-link" to={`/admin/medicamentos/${medication.id}`}>
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
