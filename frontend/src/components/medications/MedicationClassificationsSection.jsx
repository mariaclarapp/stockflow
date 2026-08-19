import { AlertCircle, Layers3, LoaderCircle, Plus, Settings2, Tag, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  associateMedicationClassification,
  createClassification,
  deleteClassification,
  getClassifications,
  removeMedicationClassification,
  updateClassification,
} from "../../api/medications";
import FilterSelect from "../filters/FilterSelect";
import ClassificationManagementModal from "./ClassificationManagementModal";
import { classificationStyle } from "./classificationPresentation";

function messageFromError(error, fallback) {
  return error?.message || fallback;
}

function MedicationClassificationsSection({ medication, onMedicationChange }) {
  const [classifications, setClassifications] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState("");
  const [modalError, setModalError] = useState("");

  useEffect(() => {
    let isCurrent = true;
    getClassifications()
      .then((data) => {
        if (isCurrent) setClassifications(data);
      })
      .catch((requestError) => {
        if (isCurrent) {
          setError(messageFromError(requestError, "Não foi possível carregar as classificações."));
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const associated = medication.classificacoes || [];
  const associatedIds = new Set(associated.map((item) => item.id));
  const available = classifications.filter(
    (item) => item.ativo
      && !associatedIds.has(item.id)
      && (
        !medication.subgrupo_gmus
        || item.nome?.toUpperCase() === "MANIPULADO"
      ),
  );

  async function handleAssociation() {
    if (!selectedId) return;
    setIsSubmitting(true);
    setError("");
    try {
      const updated = await associateMedicationClassification(medication.id, selectedId);
      onMedicationChange(updated);
      setSelectedId("");
    } catch (requestError) {
      setError(messageFromError(requestError, "Não foi possível associar a classificação."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRemoval(classification) {
    setIsSubmitting(true);
    setError("");
    try {
      await removeMedicationClassification(medication.id, classification.id);
      onMedicationChange({
        ...medication,
        classificacoes: associated.filter((item) => item.id !== classification.id),
      });
    } catch (requestError) {
      setError(messageFromError(requestError, "Não foi possível remover a classificação."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSave(editing, form) {
    setIsSubmitting(true);
    setModalError("");
    try {
      const saved = editing
        ? await updateClassification(editing.id, form)
        : await createClassification(form);
      setClassifications((current) =>
        [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) =>
          a.nome.localeCompare(b.nome, "pt-BR"),
        ),
      );
      if (associatedIds.has(saved.id)) {
        onMedicationChange({
          ...medication,
          classificacoes: associated.map((item) => item.id === saved.id ? saved : item),
        });
      }
      return saved;
    } catch (requestError) {
      setModalError(messageFromError(requestError, "Não foi possível salvar a classificação."));
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(classification) {
    setIsSubmitting(true);
    setModalError("");
    try {
      await deleteClassification(classification.id);
      setClassifications((current) =>
        current.filter((item) => item.id !== classification.id),
      );
      return true;
    } catch (requestError) {
      setModalError(messageFromError(requestError, "Não foi possível excluir a classificação."));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  function removalIsProtected(classification) {
    return classification.nome?.toUpperCase() === "MANIPULADO"
      && /\(\s*MANIPULADO\s*\)/i.test(medication.descricao || "");
  }

  return (
    <section className="detail-section classification-section" aria-labelledby="classifications-title">
      <div className="detail-section__heading">
        <div>
          <span className="eyebrow">Organização interna</span>
          <h2 id="classifications-title">Categorias e tags</h2>
          <p>Organize a apresentação sem alterar os dados oficiais do G-MUS.</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setModalError("");
            setIsModalOpen(true);
          }}
        >
          <Settings2 size={16} />
          Gerenciar classificações
        </button>
      </div>

      <div className="classification-association-tool">
        <div className="classification-associated-list">
          {medication.subgrupo_gmus && (
            <span className="medication-category-badge medication-category-badge--subgroup">
              <Layers3 size={12} aria-hidden="true" />
              {medication.subgrupo_gmus.codigo_gmus && (
                <>{medication.subgrupo_gmus.codigo_gmus} - </>
              )}
              {medication.subgrupo_gmus.nome}
            </span>
          )}
          {associated.map((classification) => (
            <span
              className="detail-classification-badge"
              key={classification.id}
              style={classificationStyle(classification.cor)}
            >
              <span className="classification-badge-dot" aria-hidden="true" />
              {classification.nome}
              {!classification.ativo && <em>Inativa</em>}
              <button
                type="button"
                onClick={() => handleRemoval(classification)}
                disabled={isSubmitting || removalIsProtected(classification)}
                aria-label={`Remover classificação ${classification.nome}`}
                title={removalIsProtected(classification)
                  ? "Associação protegida pelo marcador (MANIPULADO)"
                  : `Remover ${classification.nome}`}
              >
                <X size={13} />
              </button>
            </span>
          ))}
          {!medication.subgrupo_gmus && !associated.length && (
            <p className="classification-empty">Nenhuma classificação associada.</p>
          )}
        </div>

        {medication.subgrupo_gmus && (
          <p className="classification-category-guidance">
            Este medicamento já possui categoria oficial do G-MUS. Apenas a tag
            MANIPULADO pode ser adicionada como informação independente.
          </p>
        )}

        <div className="classification-association-controls">
          <FilterSelect
            id="medication-classification"
            className="classification-association-select"
            label="Adicionar classificação"
            value={selectedId}
            options={available.map((item) => ({ value: String(item.id), label: item.nome }))}
            placeholder={available.length ? "Selecione uma classificação" : "Nenhuma classificação disponível"}
            loadingLabel="Carregando classificações..."
            isLoading={isLoading || isSubmitting}
            icon={Tag}
            onChange={setSelectedId}
          />
          <button
            type="button"
            className="primary-button classification-add-button"
            onClick={handleAssociation}
            disabled={!selectedId || isSubmitting}
          >
            {isSubmitting ? <LoaderCircle className="button-spinner" size={17} /> : <Plus size={17} />}
            Adicionar classificação
          </button>
        </div>

        {error && (
          <p className="classification-section__error" role="alert">
            <AlertCircle size={16} />
            {error}
          </p>
        )}
      </div>

      {isModalOpen && (
        <ClassificationManagementModal
          classifications={classifications}
          isSaving={isSubmitting}
          error={modalError}
          onClose={() => setIsModalOpen(false)}
          onDelete={handleDelete}
          onSave={handleSave}
        />
      )}
    </section>
  );
}

export default MedicationClassificationsSection;
