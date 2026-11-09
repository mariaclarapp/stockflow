import { AlertCircle, Building2, CalendarDays, CheckCircle2, Info, LoaderCircle, Pencil, RefreshCw, SearchCheck, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import { correctMovementValidation, getAnalysisOptions, getMovementValidation } from "../api/analysis";
import StockCorrectionModal from "../components/StockCorrectionModal";
import FilterSelect from "../components/filters/FilterSelect";
import { formatCompetence, formatDecimal } from "../utils/formatters";

function requestErrorMessage(error) {
  if (error instanceof ApiError && error.status === 0) return "A API está temporariamente indisponível. Tente novamente.";
  return error instanceof ApiError ? error.message : "Não foi possível carregar as opções de análise.";
}

function SummaryCard({ label, value }) {
  return <div><small>{label}</small><strong>{formatDecimal(value || 0)}</strong></div>;
}

function optionalDecimal(value) {
  return value === null || value === undefined ? "—" : formatDecimal(value);
}

function ValidacaoPage() {
  const [options, setOptions] = useState({ competencias: [], ups: [] });
  const [competenciaId, setCompetenciaId] = useState("");
  const [upsId, setUpsId] = useState("");
  const [validation, setValidation] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isValidating, setIsValidating] = useState(false);
  const [correctionItem, setCorrectionItem] = useState(null);
  const [correctionError, setCorrectionError] = useState("");
  const [isCorrecting, setIsCorrecting] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    getAnalysisOptions()
      .then((data) => {
        if (!isCurrent) return;
        setOptions(data);
        setCompetenciaId(data.competencias[0]?.id ? String(data.competencias[0].id) : "");
        setUpsId(data.ups[0]?.id ? String(data.ups[0].id) : "");
      })
      .catch((requestError) => { if (isCurrent) setError(requestErrorMessage(requestError)); })
      .finally(() => { if (isCurrent) setIsLoading(false); });
    return () => { isCurrent = false; };
  }, []);

  const selectedCompetence = useMemo(() => options.competencias.find((item) => String(item.id) === competenciaId), [competenciaId, options.competencias]);
  const selectedUps = useMemo(() => options.ups.find((item) => String(item.id) === upsId), [options.ups, upsId]);
  const validationIncomplete = validation && validation.totais.fora_da_validacao > 0;
  const validationSucceeded = validation && validation.totais.divergentes === 0 && validation.totais.comparaveis > 0;

  async function validateMovements() {
    if (!competenciaId || !upsId) return;
    setError("");
    setValidation(null);
    setIsValidating(true);
    try {
      setValidation(await getMovementValidation(competenciaId, upsId));
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setIsValidating(false);
    }
  }

  function openCorrection(item) {
    setCorrectionError("");
    setCorrectionItem(item);
  }

  function closeCorrection() {
    if (isCorrecting) return;
    setCorrectionItem(null);
    setCorrectionError("");
  }

  async function saveCorrection({ correctedStock, reason }) {
    if (!correctionItem) return;
    setCorrectionError("");
    setIsCorrecting(true);
    try {
      await correctMovementValidation({
        competencia: competenciaId,
        ups: upsId,
        medicamento: correctionItem.medicamento.id,
        estoqueCorrigido: correctedStock,
        justificativa: reason,
      });
      const updatedValidation = await getMovementValidation(competenciaId, upsId);
      setValidation(updatedValidation);
      setCorrectionItem(null);
    } catch (requestError) {
      setCorrectionError(requestErrorMessage(requestError));
    } finally {
      setIsCorrecting(false);
    }
  }

  return (
    <main className="analysis-page">
      <header className="page-heading"><div><span className="eyebrow">Conferência mensal</span><h1>Validação de estoque</h1><p>Confira o saldo usando o estoque anterior e as movimentações da competência.</p></div></header>
      <section className="analysis-card">
        <div className="analysis-card__heading"><SearchCheck size={21} aria-hidden="true" /><div><h2>Validar movimentações</h2><p>Estoque anterior + entradas − saídas = estoque final.</p></div></div>
        <div className="validation-explanation"><Info size={17} aria-hidden="true" /><p>Selecione a competência e a UPS para comparar o saldo esperado com o estoque observado. Divergências ficam disponíveis para correção manual no detalhamento.</p></div>
        <div className="analysis-filters">
          <FilterSelect id="analysis-competence" label="Competência" icon={CalendarDays} value={competenciaId} options={options.competencias.map((item) => ({ value: item.id, label: formatCompetence(item) }))} placeholder="Selecione uma competência" isLoading={isLoading} loadingLabel="Carregando competências..." onChange={setCompetenciaId} />
          <FilterSelect id="analysis-ups" label="UPS" icon={Building2} value={upsId} options={options.ups.map((item) => ({ value: item.id, label: item.nome }))} placeholder="Selecione uma UPS" isLoading={isLoading} loadingLabel="Carregando UPS..." onChange={setUpsId} />
          <button className="primary-button analysis-submit" type="button" onClick={validateMovements} disabled={!competenciaId || !upsId || isLoading || isValidating}>{isValidating ? <LoaderCircle className="button-spinner" size={17} /> : <RefreshCw size={17} />}<span>{isValidating ? "Validando..." : "Validar estoque"}</span></button>
        </div>
      </section>
      {error && <div className="request-feedback request-feedback--error dashboard-error" role="alert"><AlertCircle size={18} /><p>{error}</p></div>}
      {validation && <section className="analysis-card analysis-result" aria-live="polite">
        <header className="analysis-result__header"><div><span className="eyebrow">Resultado da validação</span><h2>{selectedCompetence ? formatCompetence(selectedCompetence) : "Competência"}</h2><p>{selectedUps?.nome || validation.ups.nome}</p></div><div className="analysis-result__status"><strong className={`analysis-result__status-badge ${validationSucceeded ? "analysis-result__status-badge--ok" : "analysis-result__status-badge--warning"}`}>{validation.totais.divergentes ? `${validation.totais.divergentes} divergência(s)` : validationSucceeded ? "Validado" : "Sem itens validados"}</strong><small>{validation.totais.medicamentos_novos} medicamento(s) novo(s) · {validation.totais.correcoes_manuais || 0} correção(ões) manual(is)</small></div></header>
        <p className="analysis-note">Os valores abaixo são calculados a partir dos relatórios de estoque e movimentações.</p>
        <h3 className="analysis-section-title">Resumo do estoque</h3>
        <div className="analysis-totals"><SummaryCard label="Estoque anterior" value={validation.totais.estoque_anterior} /><SummaryCard label="Estoque esperado" value={validation.totais.estoque_esperado} /><SummaryCard label="Estoque observado" value={validation.totais.estoque_observado} /><SummaryCard label="Diferença" value={validation.totais.diferenca} /></div>
        {validation.totais.correcoes_manuais > 0 && <p className="analysis-note analysis-note--manual"><CheckCircle2 size={16} />{validation.totais.correcoes_manuais} correção(ões) manual(is) aplicada(s). O total originalmente importado era {formatDecimal(validation.totais.estoque_observado_original)}.</p>}
        <h3 className="analysis-section-title">Movimentações consideradas</h3>
        <p className="analysis-note">Medicamentos ausentes do relatório sintético usam movimento zero quando aparecem nos dois estoques. Medicamentos novos começam com estoque anterior zero.</p>
        <div className="analysis-totals"><SummaryCard label="Entradas validadas" value={validation.movimentacoes.entradas} /><SummaryCard label="Saídas validadas" value={validation.movimentacoes.saidas} /><SummaryCard label="Saldo líquido validado" value={validation.movimentacoes.saldo_liquido} /><SummaryCard label="Medicamentos validados" value={validation.totais.comparaveis} /></div>
        <details className="validation-detail-disclosure">
          <summary><span><SearchCheck size={17} aria-hidden="true" /><strong>Detalhamento do relatório completo</strong></span><small>Linhas reconhecidas, movimentos e correções</small></summary>
          <div className="validation-detail-disclosure__content">
            <p className="analysis-note">Os valores abaixo representam todas as linhas reconhecidas no relatório de movimentações, inclusive itens que não puderam ser conciliados individualmente.</p>
            <div className="analysis-movement-details"><div><span>Compras</span><strong>{formatDecimal(validation.movimentacoes.compra)}</strong></div><div><span>Transferências recebidas</span><strong>{formatDecimal(validation.movimentacoes.transferencia_entrada)}</strong></div><div><span>Transferências enviadas</span><strong>{formatDecimal(validation.movimentacoes.transferencia_saida)}</strong></div><div><span>Acertos de entrada</span><strong>{formatDecimal(validation.movimentacoes.acerto_entrada)}</strong></div><div><span>Acertos de saída</span><strong>{formatDecimal(validation.movimentacoes.acerto_saida)}</strong></div><div><span>Devoluções/retornos</span><strong>{formatDecimal(validation.movimentacoes.devolucoes)}</strong></div></div>
            {validationIncomplete && <p className="analysis-note">{validation.totais.fora_da_validacao} item(ns) ficou(aram) fora da validação; {validation.totais.sem_saldo_final} não possui(em) saldo final nesta competência. Isso não altera o resultado dos medicamentos validados acima.</p>}
            <div className="analysis-table-wrapper">
          <table className="analysis-table validation-table">
            <thead><tr><th>Medicamento</th><th>Anterior</th><th>Entradas</th><th>Saídas</th><th>Esperado</th><th>Observado</th><th>Situação</th><th>Ação necessária</th></tr></thead>
            <tbody>{validation.registros.map((item) => <tr key={item.medicamento.id}>
              <td><strong>{item.medicamento.descricao}</strong><small>{item.medicamento.codigo_gmus}</small></td>
              <td>{optionalDecimal(item.estoque_anterior)}</td>
              <td>{optionalDecimal(item.entradas)}</td>
              <td>{optionalDecimal(item.saidas)}</td>
              <td>{optionalDecimal(item.estoque_esperado)}</td>
              <td>{item.correcao_manual ? <span className="manual-correction-value"><s>{optionalDecimal(item.estoque_observado_original)}</s><strong>{optionalDecimal(item.estoque_observado)}</strong></span> : optionalDecimal(item.estoque_observado)}</td>
              <td>{item.situacao === "conferido" ? <span className="analysis-status analysis-status--ok"><CheckCircle2 size={15} />{item.correcao_manual ? "Validado · manual" : item.estoque_anterior_inferido ? "Validado · novo" : "Validado"}</span> : item.situacao === "divergente" ? <span className="analysis-status analysis-status--warning"><XCircle size={15} />Divergente</span> : <span className="analysis-status">{item.estoque_observado === null ? "Sem saldo final" : "Sem base anterior"}</span>}</td>
              <td>{item.situacao === "divergente" ? <button className="validation-correction-button" type="button" onClick={() => openCorrection(item)}><Pencil size={14} />Corrigir</button> : <span className="validation-no-action">—</span>}</td>
            </tr>)}</tbody>
          </table>
            </div>
          </div>
        </details>
      </section>}
      {correctionItem && <StockCorrectionModal key={correctionItem.medicamento.id} error={correctionError} isSubmitting={isCorrecting} item={correctionItem} onCancel={closeCorrection} onConfirm={saveCorrection} />}
    </main>
  );
}

export default ValidacaoPage;
