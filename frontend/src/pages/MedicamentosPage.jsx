import {
  AlertCircle,
  CalendarDays,
  LoaderCircle,
  MapPin,
  Pill,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import {
  getClassifications,
  getMedications,
  getMedicationOptions,
  getMedicationSubgroups,
} from "../api/medications";
import MedicationFilters from "../components/medications/MedicationFilters";
import MedicationList from "../components/medications/MedicationList";

function medicationFilters({
  appliedSearch,
  categoryValue,
  competenceId,
  upsId,
  unit,
  stockStatus,
  validationStatus,
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
    validationStatus,
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
  const [validationStatus, setValidationStatus] = useState("");
  const [ordering, setOrdering] = useState("descricao");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [error, setError] = useState("");
  const [categoryError, setCategoryError] = useState("");

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
            validationStatus,
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
  }, [appliedSearch, categoryValue, competenceId, upsId, unit, stockStatus, validationStatus, ordering]);

  function handleSearch(event) {
    event.preventDefault();
    setAppliedSearch(searchInput.trim());
  }

  function clearSearch() {
    setSearchInput("");
    setAppliedSearch("");
  }

  function clearFilters() {
    setSearchInput("");
    setAppliedSearch("");
    setCategoryValue("");
    setCompetenceId(defaultCompetenceId);
    setUpsId("");
    setUnit("");
    setStockStatus("");
    setValidationStatus("");
    setOrdering("descricao");
  }

  function changeCategory(value) {
    setCategoryValue(value);
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
          validationStatus={validationStatus}
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
          onCompetenceChange={setCompetenceId}
          onUpsChange={setUpsId}
          onUnitChange={setUnit}
          onStockStatusChange={setStockStatus}
          onValidationStatusChange={setValidationStatus}
          onOrderingChange={setOrdering}
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
          {(appliedSearch || categoryValue || upsId || unit || stockStatus || validationStatus || ordering !== "descricao") && !isLoading && (
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
            />
          )}
        </div>
      </section>

    </main>
  );
}

export default MedicamentosPage;
