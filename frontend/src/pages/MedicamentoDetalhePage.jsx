import { AlertCircle, ArrowLeft, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getMedicationDetail } from "../api/medications";
import CurrentStockSection from "../components/medications/CurrentStockSection";
import HistorySection from "../components/medications/HistorySection";
import MedicationClassificationsSection from "../components/medications/MedicationClassificationsSection";
import MedicationDetailHeader from "../components/medications/MedicationDetailHeader";

function requestErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    return "Não foi possível carregar os dados do medicamento.";
  }
  if (error.status === 0) return "A API está temporariamente indisponível.";
  if (error.status === 200) return "A API retornou uma resposta inesperada.";
  if (error.status === 401 || error.status === 403) {
    return "Sua sessão não está disponível. Entre novamente.";
  }
  return error.message || "Não foi possível carregar os dados do medicamento.";
}

function MedicamentoDetalhePage() {
  const { id } = useParams();
  const [medication, setMedication] = useState(null);
  const [history, setHistory] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let isCurrent = true;

    async function loadDetail() {
      setIsLoading(true);
      setError("");
      setNotFound(false);
      try {
        const data = await getMedicationDetail(id);
        if (isCurrent) {
          setMedication(data.medication);
          setHistory(data.history);
        }
      } catch (requestError) {
        if (!isCurrent) return;
        setMedication(null);
        setHistory(null);
        if (requestError instanceof ApiError && requestError.status === 404) {
          setNotFound(true);
        } else {
          setError(requestErrorMessage(requestError));
        }
      } finally {
        if (isCurrent) setIsLoading(false);
      }
    }

    loadDetail();
    return () => {
      isCurrent = false;
    };
  }, [id, requestVersion]);

  if (isLoading) {
    return (
      <main className="medication-detail-page">
        <div className="detail-page-state" aria-live="polite">
          <LoaderCircle className="button-spinner" size={30} />
          <strong>Carregando medicamento e histórico...</strong>
        </div>
      </main>
    );
  }

  if (notFound) {
    return (
      <main className="medication-detail-page">
        <div className="detail-page-state detail-page-state--error">
          <AlertCircle size={32} />
          <h1>Medicamento não encontrado</h1>
          <p>O medicamento informado não existe ou não está mais disponível.</p>
          <Link className="secondary-button" to="/admin/medicamentos">
            <ArrowLeft size={16} />
            Voltar para medicamentos
          </Link>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="medication-detail-page">
        <div className="detail-page-state detail-page-state--error" role="alert">
          <AlertCircle size={32} />
          <h1>Não foi possível exibir o medicamento</h1>
          <p>{error}</p>
          <div className="detail-page-state__actions">
            <button
              type="button"
              className="primary-button detail-retry-button"
              onClick={() => setRequestVersion((version) => version + 1)}
            >
              <RefreshCw size={16} />
              Tentar novamente
            </button>
            <Link className="secondary-button" to="/admin/medicamentos">
              Voltar
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="medication-detail-page">
      <MedicationDetailHeader medication={medication} />
      <MedicationClassificationsSection
        medication={medication}
        onMedicationChange={setMedication}
      />
      <CurrentStockSection
        stock={history.estoque_atual}
        totalQuantity={medication.quantidade_estoque_total}
        unit={medication.unidade}
      />
      <HistorySection history={history.historico} unit={medication.unidade} />
    </main>
  );
}

export default MedicamentoDetalhePage;
