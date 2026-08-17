import { AlertCircle, LoaderCircle, SearchX } from "lucide-react";
import { useRef, useState } from "react";

import { ApiError } from "../api/client";
import { getPublicMedications } from "../api/publicMedications";
import PublicHeader from "../components/public/PublicHeader";
import PublicMedicationResults from "../components/public/PublicMedicationResults";
import PublicMedicationSearch from "../components/public/PublicMedicationSearch";

function requestErrorMessage(error) {
  if (error instanceof ApiError && error.status === 0) {
    return "Não foi possível conectar ao serviço de consulta. Tente novamente em alguns instantes.";
  }
  return "Não foi possível realizar a consulta agora. Tente novamente.";
}

function PublicMedicamentosPage() {
  const [searchInput, setSearchInput] = useState("");
  const [searchedTerm, setSearchedTerm] = useState("");
  const [medications, setMedications] = useState(null);
  const [guidance, setGuidance] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const requestSequence = useRef(0);

  function handleSearchChange(value) {
    setSearchInput(value);
    setGuidance("");
  }

  function handleClear() {
    requestSequence.current += 1;
    setSearchInput("");
    setSearchedTerm("");
    setMedications(null);
    setGuidance("");
    setError("");
    setIsLoading(false);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const term = searchInput.trim();

    if (!term) {
      setGuidance("Digite o nome de um medicamento antes de buscar.");
      setError("");
      return;
    }

    setGuidance("");
    setError("");
    setIsLoading(true);
    setSearchedTerm(term);
    const currentRequest = requestSequence.current + 1;
    requestSequence.current = currentRequest;

    try {
      const response = await getPublicMedications(term);
      if (requestSequence.current === currentRequest) {
        setMedications(response);
      }
    } catch (requestError) {
      if (requestSequence.current === currentRequest) {
        setMedications(null);
        setError(requestErrorMessage(requestError));
      }
    } finally {
      if (requestSequence.current === currentRequest) {
        setIsLoading(false);
      }
    }
  }

  return (
    <div className="public-page">
      <PublicHeader />
      <main className="public-main">
        <section className="public-intro" aria-labelledby="public-page-title">
          <span className="eyebrow">Consulta pública</span>
          <h1 id="public-page-title">Consulta de medicamentos</h1>
          <p>Pesquise uma apresentação para consultar sua disponibilidade na rede municipal.</p>
          <PublicMedicationSearch
            value={searchInput}
            isLoading={isLoading}
            onChange={handleSearchChange}
            onClear={handleClear}
            onSubmit={handleSubmit}
          />
          {guidance && <p className="public-guidance" role="status">{guidance}</p>}
        </section>

        <div className="public-query-state" aria-live="polite" aria-atomic="true">
          {isLoading && (
            <div className="public-state">
              <LoaderCircle className="button-spinner" size={27} aria-hidden="true" />
              <strong>Consultando medicamentos...</strong>
            </div>
          )}

          {!isLoading && error && (
            <div className="public-state public-state--error" role="alert">
              <AlertCircle size={27} aria-hidden="true" />
              <strong>Não foi possível concluir a pesquisa</strong>
              <p>{error}</p>
            </div>
          )}

          {!isLoading && !error && medications === null && (
            <div className="public-state public-state--initial">
              <SearchX size={28} aria-hidden="true" />
              <strong>Pesquise um medicamento para consultar a disponibilidade.</strong>
            </div>
          )}

          {!isLoading && !error && medications?.length === 0 && (
            <div className="public-state">
              <SearchX size={28} aria-hidden="true" />
              <strong>Nenhum medicamento encontrado para a pesquisa informada.</strong>
              <p>Confira o nome digitado e tente novamente.</p>
            </div>
          )}
        </div>

        {!isLoading && !error && medications?.length > 0 && (
          <PublicMedicationResults medications={medications} searchTerm={searchedTerm} />
        )}
      </main>
      <footer className="public-footer">
        <span>StockFlow · Farmácia Municipal de Ribeirão Claro</span>
      </footer>
    </div>
  );
}

export default PublicMedicamentosPage;
