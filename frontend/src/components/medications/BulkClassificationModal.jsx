import { AlertCircle, CheckCircle2, Layers3, Tag, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import FilterSelect from "../filters/FilterSelect";

function hasCommonCategory(medication) {
  return (medication.classificacoes || []).some(
    (item) => item.nome?.toUpperCase() !== "MANIPULADO",
  );
}

function BulkClassificationModal({
  classifications,
  medications,
  error,
  isSubmitting,
  onApply,
  onClose,
}) {
  const [classificationId, setClassificationId] = useState("");
  const summary = useMemo(() => {
    const withSubgroup = medications.filter((item) => item.subgrupo_gmus).length;
    const alreadyClassified = medications.filter(
      (item) => !item.subgrupo_gmus && hasCommonCategory(item),
    ).length;
    return {
      selected: medications.length,
      eligible: medications.length - withSubgroup - alreadyClassified,
      withSubgroup,
      alreadyClassified,
    };
  }, [medications]);
  const options = classifications
    .filter(
      (item) => item.ativo && item.nome?.toUpperCase() !== "MANIPULADO",
    )
    .map((item) => ({
      value: String(item.id),
      label: item.nome,
    }));

  useEffect(() => {
    function handleEscape(event) {
      if (event.key === "Escape" && !isSubmitting) onClose();
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isSubmitting, onClose]);

  function handleSubmit(event) {
    event.preventDefault();
    if (classificationId && summary.eligible > 0) {
      onApply(Number(classificationId));
    }
  }

  return (
    <div className="bulk-classification-overlay">
      <section
        className="bulk-classification-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-classification-title"
      >
        <header>
          <div>
            <span className="eyebrow">Ação em lote</span>
            <h2 id="bulk-classification-title">Classificar medicamentos</h2>
          </div>
          <button
            className="classification-icon-button"
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Fechar classificação em lote"
          >
            <X size={18} />
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="bulk-classification-summary" aria-label="Resumo da seleção">
            <p>
              <CheckCircle2 size={16} />
              <span><strong>{summary.selected}</strong> selecionados</span>
            </p>
            <p className="bulk-classification-summary__eligible">
              <Tag size={16} />
              <span><strong>{summary.eligible}</strong> serão classificados</span>
            </p>
            <p>
              <Layers3 size={16} />
              <span><strong>{summary.withSubgroup}</strong> ignorados por possuírem subgrupo</span>
            </p>
            <p>
              <AlertCircle size={16} />
              <span><strong>{summary.alreadyClassified}</strong> ignorados por já possuírem categoria</span>
            </p>
          </div>

          <div className="bulk-classification-field">
            <FilterSelect
              id="bulk-medication-category"
              label="Categoria"
              value={classificationId}
              options={options}
              placeholder="Selecione uma categoria"
              icon={Tag}
              onChange={setClassificationId}
            />
            {!options.length && (
              <p>Nenhuma categoria manual ativa está disponível.</p>
            )}
          </div>

          {error && (
            <p className="bulk-classification-error" role="alert">
              <AlertCircle size={16} />
              {error}
            </p>
          )}

          <footer>
            <button
              className="secondary-button"
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              className="primary-button"
              type="submit"
              disabled={!classificationId || summary.eligible === 0 || isSubmitting}
            >
              <Tag size={16} />
              {isSubmitting ? "Aplicando..." : "Aplicar categoria"}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}

export default BulkClassificationModal;
