import { AlertCircle, CheckCircle2, Layers3, Tag, Tags, X } from "lucide-react";
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
  mode = "classify",
  error,
  isSubmitting,
  onApply,
  onClose,
}) {
  const [classificationId, setClassificationId] = useState("");
  const isRemoving = mode === "remove";
  const summary = useMemo(() => {
    const withSubgroup = medications.filter((item) => item.subgrupo_gmus).length;
    if (isRemoving) {
      const selectedClassificationId = Number(classificationId);
      const eligible = medications.filter(
        (item) => !item.subgrupo_gmus && (
          classificationId
            ? (item.classificacoes || []).some(
              (classification) => classification.id === selectedClassificationId,
            )
            : hasCommonCategory(item)
        ),
      ).length;
      return {
        selected: medications.length,
        eligible,
        withSubgroup,
        withoutCategory: medications.length - withSubgroup - eligible,
      };
    }
    const alreadyClassified = medications.filter(
      (item) => !item.subgrupo_gmus && hasCommonCategory(item),
    ).length;
    return {
      selected: medications.length,
      eligible: medications.length - withSubgroup - alreadyClassified,
      withSubgroup,
      alreadyClassified,
    };
  }, [classificationId, isRemoving, medications]);
  const associatedClassificationIds = new Set(
    medications.flatMap((item) =>
      item.subgrupo_gmus
        ? []
        : (item.classificacoes || []).map((classification) => classification.id),
    ),
  );
  const options = classifications
    .filter(
      (item) => item.nome?.toUpperCase() !== "MANIPULADO"
        && (isRemoving ? associatedClassificationIds.has(item.id) : item.ativo),
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

  const ActionIcon = isRemoving ? Tags : Tag;

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
            <h2 id="bulk-classification-title">
              {isRemoving ? "Desclassificar medicamentos" : "Classificar medicamentos"}
            </h2>
          </div>
          <button
            className="classification-icon-button"
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label={`Fechar ${isRemoving ? "desclassificação" : "classificação"} em lote`}
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
              <ActionIcon size={16} />
              <span>
                <strong>{summary.eligible}</strong>{" "}
                {isRemoving
                  ? (classificationId ? "serão desclassificados" : "podem ser desclassificados")
                  : "serão classificados"}
              </span>
            </p>
            <p>
              <Layers3 size={16} />
              <span><strong>{summary.withSubgroup}</strong> ignorados por possuírem subgrupo</span>
            </p>
            {isRemoving ? (
              <p>
                <AlertCircle size={16} />
                <span>
                  <strong>{summary.withoutCategory}</strong>{" "}
                  {classificationId
                    ? "ignorados por não possuírem a categoria escolhida"
                    : "sem categoria manual para remover"}
                </span>
              </p>
            ) : (
              <p>
                <AlertCircle size={16} />
                <span><strong>{summary.alreadyClassified}</strong> ignorados por já possuírem categoria</span>
              </p>
            )}
          </div>

          <div className="bulk-classification-field">
            <FilterSelect
              id="bulk-medication-category"
              label={isRemoving ? "Categoria a remover" : "Categoria"}
              value={classificationId}
              options={options}
              placeholder={isRemoving ? "Selecione a categoria a remover" : "Selecione uma categoria"}
              icon={ActionIcon}
              onChange={setClassificationId}
            />
            {!options.length && (
              <p>
                {isRemoving
                  ? "Nenhuma categoria manual está associada aos medicamentos selecionados."
                  : "Nenhuma categoria manual ativa está disponível."}
              </p>
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
              <ActionIcon size={16} />
              {isSubmitting
                ? (isRemoving ? "Removendo..." : "Aplicando...")
                : (isRemoving ? "Remover categoria" : "Aplicar categoria")}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}

export default BulkClassificationModal;
