import { ArrowLeft, FlaskConical, Layers3, Pill } from "lucide-react";
import { Link } from "react-router-dom";

function safeClassificationStyle(color) {
  return /^#[0-9a-f]{3,8}$/i.test(color || "")
    ? { borderColor: color }
    : undefined;
}

function MedicationDetailHeader({ medication }) {
  const principles = medication.principios_ativos || [];
  const classifications = medication.classificacoes || [];

  return (
    <>
      <Link className="detail-back-link" to="/admin/medicamentos">
        <ArrowLeft size={17} />
        Voltar para medicamentos
      </Link>

      <header className="medication-detail-header">
        <div className="medication-detail-header__title">
          <span className="gmus-code">{medication.codigo_gmus}</span>
          <h1>{medication.descricao}</h1>
          {medication.unidade && (
            <span className="medication-detail-header__unit">
              <Pill size={15} />
              {medication.unidade}
            </span>
          )}
        </div>

        {(medication.subgrupo_gmus || principles.length > 0 || classifications.length > 0) && (
          <div className="medication-registration-summary">
            {medication.subgrupo_gmus && (
              <div className="medication-registration-summary__item">
                <Layers3 size={18} aria-hidden="true" />
                <span>
                  <small>Subgrupo G-MUS</small>
                  <strong>
                    {medication.subgrupo_gmus.codigo_gmus && (
                      <>{medication.subgrupo_gmus.codigo_gmus} - </>
                    )}
                    {medication.subgrupo_gmus.nome}
                  </strong>
                </span>
              </div>
            )}

            {principles.length > 0 && (
              <div className="medication-registration-summary__item">
                <FlaskConical size={18} aria-hidden="true" />
                <span>
                  <small>Princípios ativos</small>
                  <strong>{principles.map((item) => item.nome).join(", ")}</strong>
                </span>
              </div>
            )}

            {classifications.length > 0 && (
              <div className="medication-registration-summary__classifications">
                <small>Classificações</small>
                <div>
                  {classifications.map((classification) => (
                    <span
                      className="detail-classification-badge"
                      key={classification.id}
                      style={safeClassificationStyle(classification.cor)}
                    >
                      {classification.nome}
                      {!classification.ativo && <em>Inativa</em>}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </header>
    </>
  );
}

export default MedicationDetailHeader;
