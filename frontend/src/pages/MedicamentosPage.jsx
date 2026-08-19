import { AlertCircle, LoaderCircle, Pill } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import {
  getClassifications,
  getMedications,
  getMedicationSubgroups,
} from "../api/medications";
import MedicationFilters from "../components/medications/MedicationFilters";
import MedicationList from "../components/medications/MedicationList";

function requestErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    return "Não foi possível carregar os medicamentos. Tente novamente.";
  }
  if (error.status === 0) {
    return "A API está temporariamente indisponível. Tente novamente.";
  }
  if (error.status === 200) {
    return "A API retornou uma resposta inesperada.";
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
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [categoryValue, setCategoryValue] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);
  const [error, setError] = useState("");
  const [categoryError, setCategoryError] = useState("");

  useEffect(() => {
    let isCurrent = true;

    async function loadCategories() {
      const [subgroupResult, classificationResult] = await Promise.allSettled([
        getMedicationSubgroups(),
        getClassifications(),
      ]);
      if (!isCurrent) return;

      if (subgroupResult.status === "fulfilled") {
        setSubgroups(subgroupResult.value);
      }
      if (classificationResult.status === "fulfilled") {
        setClassifications(classificationResult.value);
      }
      if (
        subgroupResult.status === "rejected"
        || classificationResult.status === "rejected"
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
        const [categoryType, categoryId] = categoryValue.split(":");
        const data = await getMedications({
          search: appliedSearch,
          subgroupId: categoryType === "subgrupo" ? categoryId : "",
          classificationId: categoryType === "classificacao" ? categoryId : "",
        });
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
  }, [appliedSearch, categoryValue]);

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
  }

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
          classifications={classifications}
          subgroups={subgroups}
          isLoading={isLoading}
          isLoadingCategories={isLoadingCategories}
          onSearchInputChange={setSearchInput}
          onSearch={handleSearch}
          onCategoryChange={setCategoryValue}
          onClearSearch={clearSearch}
          onClearFilters={clearFilters}
        />

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
          {(appliedSearch || categoryValue) && !isLoading && (
            <span>Filtros aplicados</span>
          )}
        </div>

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
              onCategorySelect={setCategoryValue}
            />
          )}
        </div>
      </section>
    </main>
  );
}

export default MedicamentosPage;
