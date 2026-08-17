import { AlertCircle, FileUp, Info, LoaderCircle, RefreshCw } from "lucide-react";
import { useState } from "react";

import { ApiError } from "../api/client";
import { uploadInventory } from "../api/inventory";
import ImportSummary from "../components/imports/ImportSummary";
import InventoryFilePicker from "../components/imports/InventoryFilePicker";
import ReimportConfirmationModal from "../components/imports/ReimportConfirmationModal";

function validateFile(file) {
  if (!file) return "Selecione um arquivo CSV para continuar.";
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return "O relatório deve possuir a extensão .csv.";
  }
  if (file.size === 0) return "O arquivo selecionado está vazio.";
  return "";
}

function requestErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    return "Não foi possível processar a importação. Tente novamente.";
  }

  if (error.status === 409) {
    return error.message || "Esta competência e UPS já possuem uma importação de inventário.";
  }
  if (error.status === 422) {
    return error.message || "O relatório não possui registros processáveis ou contém um erro global.";
  }
  if (error.status === 400) {
    return error.message || "O arquivo não pôde ser interpretado.";
  }
  if (error.status === 401 || error.status === 403) {
    return "Sua sessão não está disponível. Entre novamente.";
  }
  if (error.status === 0) {
    return "A API está temporariamente indisponível. Tente novamente.";
  }
  return "Ocorreu um erro inesperado ao processar a importação.";
}

function ImportacoesPage() {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [resultFileName, setResultFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [canReimport, setCanReimport] = useState(false);
  const [isConfirmationOpen, setIsConfirmationOpen] = useState(false);

  function selectFile(selectedFile) {
    setFile(selectedFile);
    setError(validateFile(selectedFile));
    setResult(null);
    setCanReimport(false);
    setIsConfirmationOpen(false);
  }

  function removeFile() {
    setFile(null);
    setError("");
    setResult(null);
    setCanReimport(false);
    setIsConfirmationOpen(false);
  }

  async function processUpload({ reimportar = false } = {}) {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError("");
    setResult(null);
    setCanReimport(false);
    setIsSubmitting(true);

    try {
      const response = await uploadInventory(file, { reimportar });
      setResult(response);
      setResultFileName(file.name);
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
      setCanReimport(
        !reimportar && requestError instanceof ApiError && requestError.status === 409,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    processUpload();
  }

  function confirmReimportation() {
    setIsConfirmationOpen(false);
    processUpload({ reimportar: true });
  }

  return (
    <main className="import-page">
      <header className="page-heading import-page__heading">
        <div>
          <span className="eyebrow">Estoque mensal</span>
          <h1>Importações</h1>
          <p>Envie relatórios CSV do G-MUS para processamento do estoque.</p>
        </div>
        <span className="report-type-badge">
          <FileUp size={15} />
          Relatório de inventário
        </span>
      </header>

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="upload-card__heading">
          <div>
            <h2 id="upload-title">Enviar inventário</h2>
            <p>O conteúdo será validado e processado pelo StockFlow.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <InventoryFilePicker
            file={file}
            disabled={isSubmitting}
            onChange={selectFile}
            onRemove={removeFile}
          />

          <div className="upload-card__notice">
            <Info size={17} aria-hidden="true" />
            <p>
              Se a competência e a UPS já tiverem sido importadas, a substituição
              precisará ser confirmada antes do processamento.
            </p>
          </div>

          {error && (
            <div className="request-feedback request-feedback--error import-error" role="alert">
              <AlertCircle size={18} aria-hidden="true" />
              <div>
                <p>{error}</p>
                {canReimport && (
                  <button
                    className="secondary-button import-error__action"
                    type="button"
                    onClick={() => setIsConfirmationOpen(true)}
                  >
                    <RefreshCw size={15} aria-hidden="true" />
                    Reimportar e substituir
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="upload-card__actions">
            <button
              className="primary-button upload-button"
              type="submit"
              disabled={!file || isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <LoaderCircle className="button-spinner" size={18} />
                  Processando...
                </>
              ) : (
                <>
                  <FileUp size={18} />
                  Enviar inventário
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      <div className="result-announcer" aria-live="polite" aria-atomic="true">
        {isSubmitting && "Importação em processamento."}
        {result && `Importação finalizada com status ${result.status}.`}
      </div>

      {result && <ImportSummary result={result} fileName={resultFileName} />}

      {isConfirmationOpen && (
        <ReimportConfirmationModal
          isSubmitting={isSubmitting}
          onCancel={() => setIsConfirmationOpen(false)}
          onConfirm={confirmReimportation}
        />
      )}
    </main>
  );
}

export default ImportacoesPage;
