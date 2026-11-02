import { AlertCircle, FileText, FileUp, Info, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { deleteImport, getImports, previewImport, uploadMovement, uploadStock } from "../api/inventory";
import FilterSelect from "../components/filters/FilterSelect";
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
  const [preview, setPreview] = useState(null);
  const [isPreviewing, setIsPreviewing] = useState(false);

  const reportLabel = reportType === "estoque" ? "Consulta de Estoque" : "movimentações";

  useEffect(() => {
    getImports()
      .then((data) => setImports(Array.isArray(data) ? data : data.results || []))
      .catch((requestError) => setError(requestErrorMessage(requestError)))
      .finally(() => setIsLoadingImports(false));
  }, []);

  function removeFile() {
    setFile(null);
    setError("");
    setResult(null);
    setCanReimport(false);
    setIsConfirmationOpen(false);
    setPreview(null);
  }

  async function inspectFile(selectedFile) {
    setFile(selectedFile);
    setResult(null);
    setPreview(null);
    const validationError = validateFile(selectedFile);
    setError(validationError);
    if (validationError) return;
    setIsPreviewing(true);
    try {
      const data = await previewImport(selectedFile);
      const expectedType = reportType === "estoque" ? "estoque" : "movimentacao";
      if (data.tipo_relatorio !== expectedType) {
        setError(
          expectedType === "estoque"
            ? "O arquivo selecionado não é uma Consulta de Estoque."
            : "O arquivo selecionado não é uma Movimentação de Estoque sintética.",
        );
      }
      setPreview(data);
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setIsPreviewing(false);
    }
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
      try {
        const updatedImports = await getImports();
        setImports(Array.isArray(updatedImports) ? updatedImports : updatedImports.results || []);
      } catch {
        // A importação já foi concluída. Uma falha ao atualizar o histórico não
        // deve substituir o resultado de sucesso nem sugerir que o upload falhou.
      }
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
      </header>

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="upload-card__heading"><div><h2 id="upload-title">Enviar {reportLabel}</h2><p>O conteúdo será validado e processado pelo StockFlow.</p></div></div>
        <form onSubmit={(event) => { event.preventDefault(); processUpload(); }}>
          <FilterSelect
            id="report-type"
            className="report-type-select"
            label="Tipo de relatório"
            value={reportType}
            options={[
              { value: "estoque", label: "Consulta de Estoque (saldo total)" },
              { value: "movimentacao", label: "Movimentações de Estoque (sintético)" },
            ]}
            placeholder="Selecione o tipo de relatório"
            isLoading={isSubmitting}
            loadingLabel="Processando relatório..."
            icon={FileText}
            allowEmpty={false}
            onChange={(value) => {
              setReportType(value);
              removeFile();
            }}
          />
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
          <InventoryFilePicker file={file} disabled={isSubmitting || isPreviewing} onChange={inspectFile} onRemove={removeFile} reportLabel={reportLabel} />
          {isPreviewing && <div className="import-preview import-preview--loading"><LoaderCircle className="button-spinner" size={18} /><span>Analisando o arquivo antes da importação...</span></div>}
          {preview && !isPreviewing && <section className={`import-preview${preview.pode_importar ? "" : " import-preview--warning"}`} aria-label="Pré-visualização da importação"><div><small>Relatório identificado</small><strong>{preview.tipo_relatorio === "estoque" ? "Consulta de Estoque" : "Movimentações de Estoque"}</strong></div><div><small>Competência</small><strong>{preview.competencia ? `${String(preview.competencia.mes).padStart(2, "0")}/${preview.competencia.ano}` : "Não identificada"}</strong></div><div><small>UPS</small><strong>{preview.ups?.nome || "Não identificada"}</strong></div><div><small>Registros reconhecidos</small><strong>{preview.registros_identificados}</strong></div><p>{preview.pode_importar ? "Arquivo reconhecido e pronto para processamento." : "O arquivo possui um erro global e não pode ser importado."}</p></section>}
          {error && <div className="request-feedback request-feedback--error import-error" role="alert"><AlertCircle size={18} aria-hidden="true" /><div><p>{error}</p>{canReimport && <button className="secondary-button import-error__action" type="button" onClick={() => setIsConfirmationOpen(true)}><RefreshCw size={15} aria-hidden="true" />Reimportar e substituir</button>}</div></div>}
          <div className="upload-card__submission">
            <div className="upload-card__notice"><Info size={17} aria-hidden="true" /><p>Se a competência e a UPS já tiverem sido importadas, a substituição será confirmada antes do processamento.</p></div>
            <div className="upload-card__actions"><button className="primary-button upload-button" type="submit" disabled={!file || isSubmitting || isPreviewing || !preview?.pode_importar || error}>{isSubmitting ? <><LoaderCircle className="button-spinner" size={18} />Processando...</> : <><FileUp size={18} />Enviar {reportLabel}</>}</button></div>
          </div>
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
