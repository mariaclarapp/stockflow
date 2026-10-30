import { AlertCircle, FileUp, Info, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { deleteImport, getImports, uploadMovement, uploadStock } from "../api/inventory";
import ImportSummary from "../components/imports/ImportSummary";
import InventoryFilePicker from "../components/imports/InventoryFilePicker";
import ReimportConfirmationModal from "../components/imports/ReimportConfirmationModal";

function validateFile(file) {
  if (!file) return "Selecione um arquivo CSV para continuar.";
  if (!file.name.toLowerCase().endsWith(".csv")) return "O relatório deve possuir a extensão .csv.";
  if (file.size === 0) return "O arquivo selecionado está vazio.";
  return "";
}

function requestErrorMessage(error) {
  if (!(error instanceof ApiError)) return "Não foi possível processar a importação. Tente novamente.";
  if (error.status === 409) return error.message || "Esta competência, UPS e tipo de relatório já possuem uma importação.";
  if (error.status === 422) return error.message || "O relatório não possui registros processáveis ou contém um erro global.";
  if (error.status === 400) return error.message || "O arquivo não pôde ser interpretado.";
  if (error.status === 401 || error.status === 403) return "Sua sessão não está disponível. Entre novamente.";
  if (error.status === 0) return "A API está temporariamente indisponível. Tente novamente.";
  return "Ocorreu um erro inesperado ao processar a importação.";
}

function ImportacoesPage() {
  const [file, setFile] = useState(null);
  const [reportType, setReportType] = useState("estoque");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [resultFileName, setResultFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [canReimport, setCanReimport] = useState(false);
  const [isConfirmationOpen, setIsConfirmationOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [imports, setImports] = useState([]);
  const [isLoadingImports, setIsLoadingImports] = useState(true);

  const reportLabel = reportType === "estoque" ? "Consulta de Estoque" : "movimentações";

  useEffect(() => {
    getImports()
      .then((data) => setImports(Array.isArray(data) ? data : data.results || []))
      .finally(() => setIsLoadingImports(false));
  }, []);

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
      const upload = reportType === "estoque" ? uploadStock : uploadMovement;
      const response = await upload(file, { reimportar });
      setResult(response);
      setResultFileName(file.name);
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
      setCanReimport(!reimportar && requestError instanceof ApiError && requestError.status === 409);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteImport(importacao) {
    if (!window.confirm(`Excluir a importação ${importacao.nome_arquivo || "selecionada"}?`)) return;
    setIsDeleting(true);
    setError("");
    try {
      await deleteImport(importacao.id);
      setImports((current) => current.filter((item) => item.id !== importacao.id));
      if (result?.importacao_id === importacao.id) removeFile();
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <main className="import-page">
      <header className="page-heading import-page__heading">
        <div><span className="eyebrow">Estoque mensal</span><h1>Importações</h1><p>Envie relatórios CSV do G-MUS para processar estoque e movimentações.</p></div>
        <span className="report-type-badge"><FileUp size={15} />{reportType === "estoque" ? "Consulta de Estoque" : "Movimentações de Estoque"}</span>
      </header>

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="upload-card__heading"><div><h2 id="upload-title">Enviar {reportLabel}</h2><p>O conteúdo será validado e processado pelo StockFlow.</p></div></div>
        <form onSubmit={(event) => { event.preventDefault(); processUpload(); }}>
          <label className="field-label" htmlFor="report-type">Tipo de relatório
            <select id="report-type" value={reportType} onChange={(event) => { setReportType(event.target.value); removeFile(); }} disabled={isSubmitting}>
              <option value="estoque">Consulta de Estoque (saldo total)</option>
              <option value="movimentacao">Movimentações de Estoque (sintético)</option>
            </select>
          </label>
          <details className="import-download-guide">
            <summary>
              <Info size={18} aria-hidden="true" />
              <span>
                <strong>Como baixar este relatório no G-MUS</strong>
                <small>Confira o caminho e os filtros antes de exportar o CSV.</small>
              </span>
            </summary>
            <div className="import-download-guide__content">
              {reportType === "estoque" ? (
                <>
                  <p className="import-download-guide__path"><strong>Caminho:</strong> Relatórios → Estoque → Gerenciais → Estoque</p>
                  <ol>
                    <li>Selecione somente a UPS que será importada.</li>
                    <li>Informe a competência desejada e gere a <strong>Consulta de Estoque</strong>.</li>
                    <li>Exporte em CSV e mantenha um arquivo separado para cada UPS e competência.</li>
                  </ol>
                </>
              ) : (
                <>
                  <p className="import-download-guide__path"><strong>Caminho:</strong> Relatórios → Estoque → Gerenciais → Movimentação Geral do Estoque</p>
                  <ol>
                    <li>Selecione a mesma UPS usada nos relatórios de estoque.</li>
                    <li>Use o primeiro e o último dia da competência como período.</li>
                    <li>Escolha o formato <strong>Sintético</strong> e exporte em CSV.</li>
                  </ol>
                </>
              )}
              <p className="import-download-guide__example">
                <strong>Para validar agosto:</strong> importe o estoque de julho, as movimentações de agosto e o estoque de agosto.
              </p>
            </div>
          </details>
          <InventoryFilePicker file={file} disabled={isSubmitting} onChange={(selectedFile) => { setFile(selectedFile); setError(validateFile(selectedFile)); setResult(null); }} onRemove={removeFile} reportLabel={reportLabel} />
          <div className="upload-card__notice"><Info size={17} aria-hidden="true" /><p>Se a competência e a UPS já tiverem sido importadas, a substituição será confirmada antes do processamento.</p></div>
          {error && <div className="request-feedback request-feedback--error import-error" role="alert"><AlertCircle size={18} aria-hidden="true" /><div><p>{error}</p>{canReimport && <button className="secondary-button import-error__action" type="button" onClick={() => setIsConfirmationOpen(true)}><RefreshCw size={15} aria-hidden="true" />Reimportar e substituir</button>}</div></div>}
          <div className="upload-card__actions"><button className="primary-button upload-button" type="submit" disabled={!file || isSubmitting}>{isSubmitting ? <><LoaderCircle className="button-spinner" size={18} />Processando...</> : <><FileUp size={18} />Enviar {reportLabel}</>}</button></div>
        </form>
      </section>

      <section className="import-history" aria-labelledby="import-history-title">
        <div className="import-history__heading"><div><span className="eyebrow">Histórico</span><h2 id="import-history-title">Importações realizadas</h2></div></div>
        {isLoadingImports ? <p className="import-history__empty">Carregando importações...</p> : imports.length === 0 ? <p className="import-history__empty">Nenhuma importação registrada.</p> : <div className="import-history__list">{imports.map((item) => <article className="import-history__item" key={item.id}><div><strong>{item.nome_arquivo}</strong><span>{item.tipo_relatorio} · {String(item.competencia?.mes).padStart(2, "0")}/{item.competencia?.ano} · {item.ups?.nome}</span></div><button className="secondary-button secondary-button--danger" type="button" onClick={() => handleDeleteImport(item)} disabled={isDeleting}>Excluir</button></article>)}</div>}
      </section>

      <div className="result-announcer" aria-live="polite" aria-atomic="true">{isSubmitting && "Importação em processamento."}{result && `Importação finalizada com status ${result.status}.`}</div>
      {result && <ImportSummary result={result} fileName={resultFileName} onDelete={() => handleDeleteImport({ id: result.importacao_id, nome_arquivo: resultFileName })} isDeleting={isDeleting} />}
      {isConfirmationOpen && <ReimportConfirmationModal isSubmitting={isSubmitting} onCancel={() => setIsConfirmationOpen(false)} onConfirm={() => { setIsConfirmationOpen(false); processUpload({ reimportar: true }); }} />}
    </main>
  );
}

export default ImportacoesPage;
