import { AlertCircle, AlertTriangle, CalendarDays, FileText, FileUp, Info, LoaderCircle, RefreshCw, Trash2, Warehouse } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import { deleteImport, getImports, previewImport, uploadMovement, uploadStock } from "../api/inventory";
import FilterSelect from "../components/filters/FilterSelect";
import ImportSummary from "../components/imports/ImportSummary";
import InventoryFilePicker from "../components/imports/InventoryFilePicker";
import PendingImportResolutions from "../components/imports/PendingImportResolutions";
import ReimportConfirmationModal from "../components/imports/ReimportConfirmationModal";
import { useSearchParams } from "react-router-dom";

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

function formatImportDate(value) {
  if (!value) return "Data não informada";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function ImportacoesPage() {
  const [searchParams] = useSearchParams();
  const [file, setFile] = useState(null);
  const [reportType, setReportType] = useState("estoque");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [resultFileName, setResultFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [canReimport, setCanReimport] = useState(false);
  const [isConfirmationOpen, setIsConfirmationOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [imports, setImports] = useState([]);
  const [isLoadingImports, setIsLoadingImports] = useState(true);
  const [preview, setPreview] = useState(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [competenceFilter, setCompetenceFilter] = useState("");
  const [upsFilter, setUpsFilter] = useState("");
  const [reportTypeFilter, setReportTypeFilter] = useState("");

  const reportLabel = reportType === "estoque" ? "Consulta de Estoque" : "movimentações";

  const competenceOptions = useMemo(() => (
    [...new Map(
      imports
        .filter((item) => item.competencia)
        .map((item) => {
          const { ano, mes } = item.competencia;
          return [`${ano}-${mes}`, { value: `${ano}-${mes}`, label: `${String(mes).padStart(2, "0")}/${ano}`, ano, mes }];
        }),
    ).values()]
      .sort((first, second) => second.ano - first.ano || second.mes - first.mes)
  ), [imports]);

  const upsOptions = useMemo(() => (
    [...new Map(
      imports
        .filter((item) => item.ups)
        .map((item) => [String(item.ups.id), { value: String(item.ups.id), label: item.ups.nome }]),
    ).values()]
      .sort((first, second) => first.label.localeCompare(second.label, "pt-BR"))
  ), [imports]);

  const reportTypeOptions = [
    { value: "estoque", label: "Consulta de Estoque" },
    { value: "movimentacao", label: "Movimentações" },
  ];

  const visibleImports = useMemo(() => imports.filter((item) => {
    const competence = item.competencia;
    const matchesCompetence = !competenceFilter
      || `${competence?.ano}-${competence?.mes}` === competenceFilter;
    const matchesUps = !upsFilter || String(item.ups?.id) === upsFilter;
    const matchesReportType = !reportTypeFilter || item.tipo_relatorio === reportTypeFilter;
    return matchesCompetence && matchesUps && matchesReportType;
  }), [competenceFilter, imports, reportTypeFilter, upsFilter]);

  useEffect(() => {
    getImports()
      .then((data) => setImports(Array.isArray(data) ? data : data.results || []))
      .catch((requestError) => setError(requestErrorMessage(requestError)))
      .finally(() => setIsLoadingImports(false));
  }, []);

  useEffect(() => {
    const importacaoId = searchParams.get("importacao");
    if (!importacaoId || isLoadingImports) return;
    document.getElementById(`importacao-${importacaoId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [isLoadingImports, searchParams]);

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

  function handleUploadSubmit(event) {
    event.preventDefault();
    if (preview?.importacao_existente) {
      setIsConfirmationOpen(true);
      return;
    }
    processUpload();
  }

  async function handleDeleteImport() {
    if (!deleteTarget) return;
    const importacao = deleteTarget;
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
      setDeleteTarget(null);
    }
  }

  function handleImportUpdated(resolution) {
    const updatedImport = resolution.importacao || resolution;
    const resolvedPending = resolution.pendencia;
    setImports((current) => current.map((item) => (
      item.id === updatedImport.id ? updatedImport : item
    )));
    setResult((current) => {
      if (!current || current.importacao_id !== updatedImport.id) return current;
      return {
        ...current,
        status: updatedImport.status,
        quantidade_nao_associada: updatedImport.quantidade_nao_associada,
        pendencias: updatedImport.pendencias,
        registros_processados: resolvedPending
          ? Number(current.registros_processados || 0) + 1
          : current.registros_processados,
        registros_ignorados: resolvedPending
          ? Math.max(0, Number(current.registros_ignorados || 0) - 1)
          : current.registros_ignorados,
        medicamentos_criados: resolution.medicamento_criado
          ? Number(current.medicamentos_criados || 0) + 1
          : current.medicamentos_criados,
        medicamentos_reutilizados: resolvedPending && !resolution.medicamento_criado
          ? Number(current.medicamentos_reutilizados || 0) + 1
          : current.medicamentos_reutilizados,
        estoques_criados: resolution.saldo_criado
          ? Number(current.estoques_criados || 0) + 1
          : current.estoques_criados,
        erros: resolvedPending
          ? (current.erros || []).filter((issue) => (
              issue.line !== resolvedPending.linha
              || issue.type !== "invalid_material"
            ))
          : current.erros,
      };
    });
  }

  return (
    <main className="import-page">
      <header className="page-heading import-page__heading">
        <div><span className="eyebrow">Estoque mensal</span><h1>Importações</h1><p>Envie relatórios CSV do G-MUS para processar estoque e movimentações.</p></div>
      </header>

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="upload-card__heading"><div><h2 id="upload-title">Enviar {reportLabel}</h2><p>O conteúdo será validado e processado pelo StockFlow.</p></div></div>
        <form onSubmit={handleUploadSubmit}>
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
                    <li>Para a análise mensal, importe também as movimentações da mesma UPS e competência. A ordem dos dois uploads não é obrigatória.</li>
                  </ol>
                </>
              ) : (
                <>
                  <p className="import-download-guide__path"><strong>Caminho:</strong> Relatórios → Estoque → Gerenciais → Movimentação Geral do Estoque</p>
                  <ol>
                    <li>Selecione a mesma UPS usada nos relatórios de estoque.</li>
                    <li>Use o primeiro e o último dia da competência como período.</li>
                    <li>Escolha o formato <strong>Sintético</strong> e exporte em CSV.</li>
                    <li>Para a análise mensal, importe também a Consulta de Estoque da mesma UPS e competência. A ordem dos dois uploads não é obrigatória.</li>
                  </ol>
                </>
              )}
              <p className="import-download-guide__example">
                <strong>Para validar agosto:</strong> disponibilize o estoque de julho, as movimentações de agosto e o estoque de agosto. A ordem de envio não é obrigatória, mas os relatórios devem corresponder à UPS e às competências indicadas.
              </p>
            </div>
          </details>
          <InventoryFilePicker file={file} disabled={isSubmitting || isPreviewing} onChange={inspectFile} onRemove={removeFile} reportLabel={reportLabel} />
          {isPreviewing && <div className="import-preview import-preview--loading"><LoaderCircle className="button-spinner" size={18} /><span>Analisando o arquivo antes da importação...</span></div>}
          {preview && !isPreviewing && <section className={`import-preview${preview.pode_importar ? "" : " import-preview--warning"}`} aria-label="Pré-visualização da importação"><div><small>Relatório identificado</small><strong>{preview.tipo_relatorio === "estoque" ? "Consulta de Estoque" : "Movimentações de Estoque"}</strong></div><div><small>Competência</small><strong>{preview.competencia ? `${String(preview.competencia.mes).padStart(2, "0")}/${preview.competencia.ano}` : "Não identificada"}</strong></div><div><small>UPS</small><strong>{preview.ups?.nome || "Não identificada"}</strong></div><div><small>Registros reconhecidos</small><strong>{preview.registros_identificados}</strong></div><p>{preview.importacao_existente ? (preview.mesmo_arquivo ? "Este mesmo arquivo já foi importado. Confirme para reprocessá-lo." : "Já existe uma importação para esta competência e UPS. Confirme para substituí-la.") : preview.pode_importar ? "Arquivo reconhecido e pronto para processamento." : "O arquivo possui um erro global e não pode ser importado."}</p></section>}
          {error && <div className="request-feedback request-feedback--error import-error" role="alert"><AlertCircle size={18} aria-hidden="true" /><div><p>{error}</p>{canReimport && <button className="secondary-button import-error__action" type="button" onClick={() => setIsConfirmationOpen(true)}><RefreshCw size={15} aria-hidden="true" />Reimportar e substituir</button>}</div></div>}
          <div className="upload-card__submission">
            <div className="upload-card__notice"><Info size={17} aria-hidden="true" /><p>Se a competência e a UPS já tiverem sido importadas, a substituição será confirmada antes do processamento.</p></div>
            <div className="upload-card__actions"><button className="primary-button upload-button" type="submit" disabled={!file || isSubmitting || isPreviewing || !preview?.pode_importar || error}>{isSubmitting ? <><LoaderCircle className="button-spinner" size={18} />Processando...</> : preview?.importacao_existente ? <><RefreshCw size={18} />Confirmar reimportação</> : <><FileUp size={18} />Enviar {reportLabel}</>}</button></div>
          </div>
        </form>
      </section>

      <section className="import-history" aria-labelledby="import-history-title">
        <div className="import-history__heading">
          <div><span className="eyebrow">Histórico</span><h2 id="import-history-title">Importações realizadas</h2></div>
          <div className="import-history__filters" aria-label="Filtros do histórico de importações">
            <FilterSelect
              id="import-history-competence"
              label="Mês"
              value={competenceFilter}
              options={competenceOptions}
              placeholder="Todos os meses"
              icon={CalendarDays}
              onChange={setCompetenceFilter}
            />
            <FilterSelect
              id="import-history-ups"
              label="UPS"
              value={upsFilter}
              options={upsOptions}
              placeholder="Todas as UPS"
              icon={Warehouse}
              onChange={setUpsFilter}
            />
            <FilterSelect
              id="import-history-report-type"
              label="Tipo"
              value={reportTypeFilter}
              options={reportTypeOptions}
              placeholder="Todos os tipos"
              icon={FileText}
              onChange={setReportTypeFilter}
            />
          </div>
        </div>
        {isLoadingImports ? <p className="import-history__empty">Carregando importações...</p> : imports.length === 0 ? <p className="import-history__empty">Nenhuma importação registrada.</p> : visibleImports.length === 0 ? <p className="import-history__empty">Nenhuma importação corresponde aos filtros selecionados.</p> : <div className="import-history__list">{visibleImports.map((item) => <article className="import-history__item" id={`importacao-${item.id}`} key={item.id}><div className="import-history__summary"><div><strong>{item.nome_arquivo}</strong><span>{item.tipo_relatorio} · {String(item.competencia?.mes).padStart(2, "0")}/{item.competencia?.ano} · {item.ups?.nome}</span><small>Importado em <b>{formatImportDate(item.data_importacao)}</b> por <b>{item.usuario || "usuário não informado"}</b></small>{item.pendencias?.length > 0 && <small className="import-history__alert">{item.pendencias.length} pendência(s) aguardando correção. Consulte os itens abaixo ou reimporte após corrigir o CSV.</small>}</div><button className="secondary-button secondary-button--danger" type="button" onClick={() => setDeleteTarget(item)} disabled={isDeleting}><Trash2 size={15} aria-hidden="true" />Excluir</button></div><PendingImportResolutions importId={item.id} pendencias={item.pendencias} onResolved={handleImportUpdated} compact /></article>)}</div>}
      </section>

      <div className="result-announcer" aria-live="polite" aria-atomic="true">{isSubmitting && "Importação em processamento."}{result && `Importação finalizada com status ${result.status}.`}</div>
      {result && <ImportSummary result={result} fileName={resultFileName} onDelete={() => setDeleteTarget({ id: result.importacao_id, nome_arquivo: resultFileName })} onImportUpdated={handleImportUpdated} isDeleting={isDeleting} />}
      {isConfirmationOpen && <ReimportConfirmationModal isSubmitting={isSubmitting} onCancel={() => setIsConfirmationOpen(false)} onConfirm={() => { setIsConfirmationOpen(false); processUpload({ reimportar: true }); }} />}
      {deleteTarget && (
        <div className="confirmation-overlay">
          <section
            className="confirmation-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-import-title"
            aria-describedby="delete-import-description"
          >
            <span className="confirmation-dialog__icon confirmation-dialog__icon--danger" aria-hidden="true">
              <AlertTriangle size={22} />
            </span>
            <div className="confirmation-dialog__content">
              <h2 id="delete-import-title">Excluir importação</h2>
              <p id="delete-import-description">
                Esta ação removerá os registros derivados desta importação. Deseja continuar?
              </p>
              <strong className="confirmation-dialog__filename">{deleteTarget.nome_arquivo || "Importação selecionada"}</strong>
            </div>
            <div className="confirmation-dialog__actions">
              <button className="secondary-button" type="button" onClick={() => setDeleteTarget(null)} disabled={isDeleting}>
                Cancelar
              </button>
              <button className="secondary-button secondary-button--danger" type="button" onClick={handleDeleteImport} disabled={isDeleting} autoFocus>
                <Trash2 size={16} aria-hidden="true" />
                {isDeleting ? "Excluindo..." : "Excluir importação"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default ImportacoesPage;
