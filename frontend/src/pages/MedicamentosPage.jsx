import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Eye,
  LoaderCircle,
  MapPin,
  Pill,
  Tag,
  Tags,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  getClassifications,
  classifyMedications,
  getMedications,
  getMedicationOptions,
  getMedicationSubgroups,
  unclassifyMedications,
} from "../api/medications";
import MedicationFilters from "../components/medications/MedicationFilters";
import MedicationList from "../components/medications/MedicationList";
import BulkClassificationModal from "../components/medications/BulkClassificationModal";

const MAX_SELECTED_MEDICATIONS = 50;

function medicationFilters({
  appliedSearch,
  categoryValue,
  competenceId,
  upsId,
  unit,
  stockStatus,
  ordering,
}) {
  const [categoryType, categoryId] = categoryValue.split(":");
  return {
    search: appliedSearch,
    subgroupId: categoryType === "subgrupo" ? categoryId : "",
    classificationId: categoryType === "classificacao" ? categoryId : "",
    uncategorized: categoryValue === "sem_categoria",
    competenceId,
    upsId,
    unit,
    stockStatus,
    ordering,
  };
}

function requestErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    return "Não foi possível carregar os medicamentos. Tente novamente.";
  }
  if (error.status === 0) {
    return "A API está temporariamente indisponível. Tente novamente.";
  }
  if (error.status === 200) {
    return error.message || "A API retornou uma resposta inesperada.";
  }
  if (error.status === 401 || error.status === 403) {
    return "Sua sessão não está disponível. Entre novamente.";
  }
  return error.message || "Não foi possível carregar os medicamentos.";
}

function MedicamentosPage() {
  const navigate = useNavigate();
  const [medications, setMedications] = useState([]);
  const [subgroups, setSubgroups] = useState([]);
  const [classifications, setClassifications] = useState([]);
  const [competencies, setCompetencies] = useState([]);
  const [upsOptions, setUpsOptions] = useState([]);
  const [units, setUnits] = useState([]);
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [categoryValue, setCategoryValue] = useState("");
  const [competenceId, setCompetenceId] = useState("");
  const [defaultCompetenceId, setDefaultCompetenceId] = useState("");
  const [upsId, setUpsId] = useState("");
  const [unit, setUnit] = useState("");
  const [stockStatus, setStockStatus] = useState("");
  const [ordering, setOrdering] = useState("descricao");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [error, setError] = useState("");
  const [categoryError, setCategoryError] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectionMessage, setSelectionMessage] = useState("");
  const [operationFeedback, setOperationFeedback] = useState("");
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [bulkMode, setBulkMode] = useState("classify");
  const [isBulkSubmitting, setIsBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState("");
  const selectionLimit = MAX_SELECTED_MEDICATIONS;

  useEffect(() => {
    let isCurrent = true;

    async function loadCategories() {
      const [subgroupResult, classificationResult, optionsResult] = await Promise.allSettled([
        getMedicationSubgroups(),
        getClassifications(),
        getMedicationOptions(),
      ]);
      if (!isCurrent) return;

      if (subgroupResult.status === "fulfilled") {
        setSubgroups(subgroupResult.value);
      }
      if (classificationResult.status === "fulfilled") {
        setClassifications(classificationResult.value);
      }
      if (optionsResult.status === "fulfilled") {
        const options = optionsResult.value;
        const initialCompetenceId = options.competencia_padrao_id
          ? String(options.competencia_padrao_id)
          : options.competencias[0]?.id
            ? String(options.competencias[0].id)
            : "";
        setCompetencies(options.competencias);
        setUpsOptions(options.ups);
        setUnits(options.unidades);
        setDefaultCompetenceId(initialCompetenceId);
        setCompetenceId(initialCompetenceId);
      }
      if (
        subgroupResult.status === "rejected"
        || classificationResult.status === "rejected"
        || optionsResult.status === "rejected"
      ) {
        setCategoryError("Não foi possível carregar todas as categorias.");
      }
      setIsLoadingCategories(false);
    }

    loadCategories();
    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    let isCurrent = true;

    async function loadMedications() {
      setIsLoading(true);
      setError("");
      try {
        const data = await getMedications(
          medicationFilters({
            appliedSearch,
            categoryValue,
            competenceId,
            upsId,
            unit,
            stockStatus,
            ordering,
          }),
        );
        if (isCurrent) setMedications(data);
      } catch (requestError) {
        if (isCurrent) {
          setMedications([]);
          setError(requestErrorMessage(requestError));
        }
      } finally {
        if (isCurrent) setIsLoading(false);
      }
    }

    loadMedications();
    return () => {
      isCurrent = false;
    };
  }, [appliedSearch, categoryValue, competenceId, upsId, unit, stockStatus, ordering]);

  function handleSearch(event) {
    event.preventDefault();
    clearSelection();
    setAppliedSearch(searchInput.trim());
  }

  function clearSearch() {
    clearSelection();
    setSearchInput("");
    setAppliedSearch("");
  }

  function clearFilters() {
    clearSelection();
    setSearchInput("");
    setAppliedSearch("");
    setCategoryValue("");
    setCompetenceId(defaultCompetenceId);
    setUpsId("");
    setUnit("");
    setStockStatus("");
    setOrdering("descricao");
  }

  function changeCategory(value) {
    clearSelection();
    setCategoryValue(value);
  }

  function toggleMedication(id) {
    setSelectionMessage("");
    setSelectedIds((current) => {
      if (current.includes(id)) return current.filter((item) => item !== id);
      if (current.length >= selectionLimit) {
        setSelectionMessage(
          `É possível selecionar no máximo ${selectionLimit} medicamentos.`,
        );
        return current;
      }
      if (current.length + 1 === selectionLimit) {
        setSelectionMessage(`Limite de ${selectionLimit} medicamentos atingido.`);
      }
      return [...current, id];
    });
  }

  function toggleAllVisible() {
    const visibleIds = medications.map((item) => item.id);
    const allVisibleSelected = visibleIds.every((id) => selectedIds.includes(id));
    setSelectionMessage("");

    if (allVisibleSelected) {
      setSelectedIds((current) => current.filter((id) => !visibleIds.includes(id)));
      return;
    }

    const missingIds = visibleIds.filter((id) => !selectedIds.includes(id));
    const availableSlots = selectionLimit - selectedIds.length;
    setSelectedIds((current) => [...current, ...missingIds.slice(0, availableSlots)]);
    if (missingIds.length > availableSlots) {
      setSelectionMessage(
        `Foram selecionados os primeiros ${selectionLimit} medicamentos visíveis. Esse é o limite da comparação.`,
      );
    } else if (selectedIds.length + missingIds.length === selectionLimit) {
      setSelectionMessage(`Limite de ${selectionLimit} medicamentos atingido.`);
    }
  }

  function clearSelection() {
    setSelectedIds([]);
    setSelectionMessage("");
  }

  function compareSelected() {
    navigate(`/admin/medicamentos/comparar?ids=${selectedIds.join(",")}`);
  }

  function openBulkClassification() {
    setBulkMode("classify");
    setBulkError("");
    setOperationFeedback("");
    setIsBulkModalOpen(true);
  }

  function openBulkDeclassification() {
    setBulkMode("remove");
    setBulkError("");
    setOperationFeedback("");
    setIsBulkModalOpen(true);
  }

  function closeBulkClassification() {
    if (!isBulkSubmitting) {
      setIsBulkModalOpen(false);
      setBulkError("");
    }
  }

  async function refreshMedicationsAfterBulkOperation() {
    try {
      const updatedMedications = await getMedications(
        medicationFilters({
          appliedSearch,
          categoryValue,
          competenceId,
          upsId,
          unit,
          stockStatus,
          ordering,
        }),
      );
      setMedications(updatedMedications);
      setError("");
    } catch (requestError) {
      setMedications([]);
      setError(requestErrorMessage(requestError));
    }
  }

  async function applyBulkClassification(classificationId) {
    setIsBulkSubmitting(true);
    setBulkError("");
    try {
      const result = await classifyMedications(selectedIds, classificationId);
      await refreshMedicationsAfterBulkOperation();
      setIsBulkModalOpen(false);
      clearSelection();
      setOperationFeedback(
        `${result.classificados} ${result.classificados === 1 ? "medicamento classificado" : "medicamentos classificados"} com sucesso.`,
      );
    } catch (requestError) {
      setBulkError(requestErrorMessage(requestError));
    } finally {
      setIsBulkSubmitting(false);
    }
  }

  async function applyBulkDeclassification(classificationId) {
    setIsBulkSubmitting(true);
    setBulkError("");
    try {
      const result = await unclassifyMedications(selectedIds, classificationId);
      await refreshMedicationsAfterBulkOperation();
      setIsBulkModalOpen(false);
      clearSelection();
      setOperationFeedback(
        `${result.desclassificados} ${result.desclassificados === 1 ? "medicamento desclassificado" : "medicamentos desclassificados"} com sucesso.`,
      );
    } catch (requestError) {
      setBulkError(requestErrorMessage(requestError));
    } finally {
      setIsBulkSubmitting(false);
    }
  }

  const selectedCompetence = competencies.find(
    (item) => String(item.id) === String(competenceId),
  );
  const selectedUps = upsOptions.find(
    (item) => String(item.id) === String(upsId),
  );
  const competenceLabel = selectedCompetence
    ? `${String(selectedCompetence.mes).padStart(2, "0")}/${selectedCompetence.ano}`
    : "Competência não selecionada";

  return (
    <main className="medications-page">
      <header className="page-heading medications-page__heading">
        <div>
          <span className="eyebrow">Cadastro de medicamentos</span>
          <h1>Medicamentos</h1>
          <p>Consulte apresentações cadastradas a partir dos relatórios do G-MUS.</p>
        </div>
        <span className="medications-page__badge">
          <Pill size={15} />
          Consulta administrativa
        </span>
      </header>

      <section className="medication-panel" aria-labelledby="medication-list-title">
        <MedicationFilters
          searchInput={searchInput}
          categoryValue={categoryValue}
          competenceId={competenceId}
          defaultCompetenceId={defaultCompetenceId}
          upsId={upsId}
          unit={unit}
          stockStatus={stockStatus}
          ordering={ordering}
          classifications={classifications}
          subgroups={subgroups}
          competencies={competencies}
          upsOptions={upsOptions}
          units={units}
          isLoading={isLoading}
          isLoadingCategories={isLoadingCategories}
          onSearchInputChange={setSearchInput}
          onSearch={handleSearch}
          onCategoryChange={changeCategory}
          onCompetenceChange={(value) => {
            clearSelection();
            setCompetenceId(value);
          }}
          onUpsChange={(value) => {
            clearSelection();
            setUpsId(value);
          }}
          onUnitChange={(value) => {
            clearSelection();
            setUnit(value);
          }}
          onStockStatusChange={(value) => {
            clearSelection();
            setStockStatus(value);
          }}
          onOrderingChange={(value) => {
            clearSelection();
            setOrdering(value);
          }}
          onClearSearch={clearSearch}
          onClearFilters={clearFilters}
        />

        <div className="medication-stock-context" role="status">
          <div>
            <CalendarDays size={18} aria-hidden="true" />
            <span>
              <small>Competência do saldo</small>
              <strong>{competenceLabel}</strong>
            </span>
          </div>
          <div>
            <MapPin size={18} aria-hidden="true" />
            <span>
              <small>Origem do estoque</small>
              <strong>{selectedUps?.nome || "Todas as UPS participantes"}</strong>
            </span>
          </div>
          <p>
            {selectedUps
              ? "Os valores exibidos pertencem somente a esta UPS."
              : "O total soma as UPS e a coluna ao lado detalha quanto pertence a cada uma."}
          </p>
        </div>

        {categoryError && (
          <div className="medication-inline-warning" role="status">
            <AlertCircle size={17} />
            <p>{categoryError} A busca textual continua disponível.</p>
          </div>
        )}

        <div className="medication-panel__summary">
          <div>
            <h2 id="medication-list-title">Apresentações cadastradas</h2>
            {!isLoading && !error && (
              <p>
                {medications.length} {medications.length === 1 ? "medicamento" : "medicamentos"} nesta consulta
              </p>
            )}
          </div>
          {(appliedSearch || categoryValue || upsId || unit || stockStatus || ordering !== "descricao") && !isLoading && (
            <span>Filtros aplicados</span>
          )}
        </div>

        {!isLoading && !error && medications.length > 0 && (
          <div className="medication-stock-summary" aria-label="Resumo da consulta">
            <div>
              <small>Com estoque</small>
              <strong>
                {medications.filter((item) => item.situacao_estoque === "disponivel").length}
              </strong>
            </div>
            <div>
              <small>Sem estoque</small>
              <strong>
                {medications.filter((item) => item.situacao_estoque === "sem_estoque").length}
              </strong>
            </div>
            <div>
              <small>Validados</small>
              <strong>
                {medications.filter((item) => item.situacao_validacao === "validado").length}
              </strong>
            </div>
            <div>
              <small>Divergentes</small>
              <strong>
                {medications.filter((item) => item.situacao_validacao === "divergente").length}
              </strong>
            </div>
          </div>
        )}

        {selectedIds.length > 0 && (
          <div className="medication-selection-bar" aria-label="Ações da seleção">
            <strong>
              <CheckCircle2 size={14} />
              {selectedIds.length} {selectedIds.length === 1 ? "selecionado" : "selecionados"}
            </strong>
            <div className="medication-selection-bar__actions">
              <button
                className="secondary-button medication-selection-classify"
                type="button"
                onClick={openBulkClassification}
              >
                <Tag size={15} />
                Classificar
              </button>
              <button
                className="secondary-button medication-selection-unclassify"
                type="button"
                onClick={openBulkDeclassification}
              >
                <Tags size={15} />
                Desclassificar
              </button>
              <button
                className="primary-button medication-selection-view"
                type="button"
                onClick={compareSelected}
                aria-label="Visualizar medicamentos selecionados"
              >
                <Eye size={16} />
                Visualizar
              </button>
              <button
                className="medication-selection-clear"
                type="button"
                onClick={clearSelection}
                aria-label="Limpar seleção de medicamentos"
              >
                <X size={15} />
                Limpar
              </button>
            </div>
          </div>
        )}

        {selectionMessage && (
          <p className="medication-selection-message" role="status">
            <AlertCircle size={16} />
            {selectionMessage}
          </p>
        )}

        {operationFeedback && (
          <p className="medication-operation-feedback" role="status">
            <CheckCircle2 size={16} />
            {operationFeedback}
          </p>
        )}

        <div aria-live="polite" aria-atomic="true">
          {isLoading ? (
            <div className="medication-loading-state">
              <LoaderCircle className="button-spinner" size={25} />
              <strong>Carregando medicamentos...</strong>
            </div>
          ) : error ? (
            <div className="medication-error-state" role="alert">
              <AlertCircle size={24} />
              <div>
                <strong>Não foi possível exibir a listagem</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : (
            <MedicationList
              medications={medications}
              selectedUpsId={upsId}
              selectedUpsName={selectedUps?.nome || ""}
              onCategorySelect={changeCategory}
              onToggleAll={toggleAllVisible}
              onToggleMedication={toggleMedication}
              selectedIds={selectedIds}
              selectionLimit={selectionLimit}
            />
          )}
        </div>
      </section>

      {isBulkModalOpen && (
        <BulkClassificationModal
          classifications={classifications}
          medications={medications.filter((item) => selectedIds.includes(item.id))}
          mode={bulkMode}
          error={bulkError}
          isSubmitting={isBulkSubmitting}
          onApply={bulkMode === "remove"
            ? applyBulkDeclassification
            : applyBulkClassification}
          onClose={closeBulkClassification}
        />
      )}
    </main>
  );
}

export default MedicamentosPage;
