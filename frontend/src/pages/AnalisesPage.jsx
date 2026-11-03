import {
  AlertCircle,
  BarChart3,
  CalendarRange,
  Download,
  LoaderCircle,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import { getAnalysisOptions, getConsumptionAnalysis } from "../api/analysis";
import { ConsumptionEvolutionChart, HorizontalBarChart } from "../components/analysis/ConsumptionCharts";
import { formatCompetence, formatDecimal } from "../utils/formatters";

const emptyFilters = {
  competenceStart: "",
  competenceEnd: "",
  upsId: "",
  search: "",
  category: "",
  unit: "",
  comparisonEnabled: false,
  comparisonStart: "",
  comparisonEnd: "",
};

function errorMessage(error) {
  if (error instanceof ApiError && error.status === 0) return "A API está indisponível no momento.";
  return error instanceof ApiError ? error.message : "Não foi possível carregar a análise.";
}

function SummaryCard({ label, value, helper }) {
  return <div className="analytics-summary-card"><small>{label}</small><strong>{value}</strong>{helper && <span>{helper}</span>}</div>;
}

function percentage(value) {
  if (value === null || value === undefined) return "Sem base anterior";
  return `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function exportRanking(data) {
  const rows = [
    ["Posição", "Código G-MUS", "Medicamento", "Unidade", "Consumo", "Média mensal", "Estoque atual", "Cobertura (dias)", "Classe ABC", "Tendência", "Participação (%)"],
    ...data.ranking.map((item, index) => [index + 1, item.codigo_gmus, item.descricao, item.unidade, item.consumo, item.media_mensal, item.estoque_atual, item.dias_cobertura, item.classe_abc, item.tendencia, item.participacao_percentual]),
  ];
  const content = `\uFEFF${rows.map((row) => row.map(csvCell).join(";")).join("\r\n")}`;
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "analise-consumo.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function AnalisesPage() {
  const [options, setOptions] = useState({ competencias: [], ups: [], subgrupos: [], classificacoes: [], unidades: [] });
  const [filters, setFilters] = useState(emptyFilters);
  const [analysis, setAnalysis] = useState(null);
  const [selectedMedicineId, setSelectedMedicineId] = useState("");
  const [rankingOrder, setRankingOrder] = useState("consumo");
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  async function loadAnalysis(nextFilters) {
    if (!nextFilters.competenceStart || !nextFilters.competenceEnd) return;
    setIsAnalyzing(true);
    setError("");
    try {
      setAnalysis(await getConsumptionAnalysis(nextFilters));
    } catch (requestError) {
      setAnalysis(null);
      setError(errorMessage(requestError));
    } finally {
      setIsAnalyzing(false);
    }
  }

  useEffect(() => {
    let active = true;
    getAnalysisOptions()
      .then((data) => {
        if (!active) return;
        const end = data.competencias[0];
        const start = data.competencias[Math.min(5, data.competencias.length - 1)];
        const nextFilters = {
          ...emptyFilters,
          competenceStart: start ? String(start.id) : "",
          competenceEnd: end ? String(end.id) : "",
        };
        setOptions(data);
        setFilters(nextFilters);
        return loadAnalysis(nextFilters);
      })
      .catch((requestError) => { if (active) setError(errorMessage(requestError)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, []);

  const categories = useMemo(() => [
    ...options.classificacoes.filter((item) => item.ativo).map((item) => ({ value: `classificacao:${item.id}`, label: item.nome })),
    ...options.subgrupos.map((item) => ({ value: `subgrupo:${item.id}`, label: item.nome || `Subgrupo ${item.codigo_gmus}` })),
  ], [options.classificacoes, options.subgrupos]);

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function submit(event) {
    event.preventDefault();
    loadAnalysis(filters);
  }

  function clearFilters() {
    const end = options.competencias[0];
    const start = options.competencias[Math.min(5, options.competencias.length - 1)];
    const nextFilters = {
      ...emptyFilters,
      competenceStart: start ? String(start.id) : "",
      competenceEnd: end ? String(end.id) : "",
    };
    setFilters(nextFilters);
    loadAnalysis(nextFilters);
  }

  const comparison = analysis?.comparacao;
  const variation = comparison?.variacao_percentual;
  const medicines = useMemo(
    () => analysis ? [...analysis.ranking, ...analysis.sem_consumo] : [],
    [analysis],
  );
  const selectedMedicine = useMemo(
    () => medicines.find((item) => String(item.id) === selectedMedicineId) || medicines[0] || null,
    [medicines, selectedMedicineId],
  );
  const orderedRanking = useMemo(() => {
    if (!analysis) return [];
    const items = [...analysis.ranking];
    if (rankingOrder === "media") return items.sort((a, b) => Number(b.media_mensal) - Number(a.media_mensal));
    if (rankingOrder === "cobertura") return items.sort((a, b) => Number(a.dias_cobertura ?? Infinity) - Number(b.dias_cobertura ?? Infinity));
    if (rankingOrder === "tendencia") return items.sort((a, b) => Number(b.tendencia_percentual ?? -Infinity) - Number(a.tendencia_percentual ?? -Infinity));
    return items;
  }, [analysis, rankingOrder]);
  const lowCoverage = useMemo(
    () => analysis ? analysis.ranking.filter((item) => item.dias_cobertura !== null).sort((a, b) => Number(a.dias_cobertura) - Number(b.dias_cobertura)).slice(0, 10) : [],
    [analysis],
  );

  return (
    <main className="analytics-page">
      <header className="page-heading"><div><span className="eyebrow">Inteligência de estoque</span><h1>Análise de consumo</h1><p>Consumo corresponde somente às saídas registradas no relatório de movimentações.</p></div></header>

      <section className="analytics-panel analytics-filter-panel">
        <div className="analytics-panel__heading"><CalendarRange size={21} /><div><h2>Período e filtros</h2><p>A média considera apenas competências com relatório de movimentação.</p></div></div>
        <form className="analytics-filters" onSubmit={submit}>
          <label className="field-label">Competência inicial<select value={filters.competenceStart} onChange={(event) => updateFilter("competenceStart", event.target.value)} disabled={isLoading}>{options.competencias.map((item) => <option key={item.id} value={item.id}>{formatCompetence(item)}</option>)}</select></label>
          <label className="field-label">Competência final<select value={filters.competenceEnd} onChange={(event) => updateFilter("competenceEnd", event.target.value)} disabled={isLoading}>{options.competencias.map((item) => <option key={item.id} value={item.id}>{formatCompetence(item)}</option>)}</select></label>
          <label className="field-label">UPS<select value={filters.upsId} onChange={(event) => updateFilter("upsId", event.target.value)}><option value="">Todas as UPS</option>{options.ups.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <label className="field-label">Categoria<select value={filters.category} onChange={(event) => updateFilter("category", event.target.value)}><option value="">Todas as categorias</option>{categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="field-label">Unidade<select value={filters.unit} onChange={(event) => updateFilter("unit", event.target.value)}><option value="">Todas as unidades</option>{options.unidades.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label className="field-label analytics-search">Medicamento<span><Search size={17} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Nome ou código G-MUS" /></span></label>
          <button className="primary-button analytics-submit" type="submit" disabled={isAnalyzing || !filters.competenceStart || !filters.competenceEnd || (filters.comparisonEnabled && (!filters.comparisonStart || !filters.comparisonEnd))}>{isAnalyzing ? <LoaderCircle className="button-spinner" size={17} /> : <BarChart3 size={17} />}Analisar</button>
          <button className="secondary-button analytics-clear" type="button" onClick={clearFilters} disabled={isAnalyzing}>Limpar filtros</button>
          <label className="analytics-comparison-toggle"><input type="checkbox" checked={filters.comparisonEnabled} onChange={(event) => updateFilter("comparisonEnabled", event.target.checked)} />Comparar com outro período</label>
          {filters.comparisonEnabled && <div className="analytics-comparison-fields"><label className="field-label">Comparação inicial<select value={filters.comparisonStart} onChange={(event) => updateFilter("comparisonStart", event.target.value)}><option value="">Selecione</option>{options.competencias.map((item) => <option key={item.id} value={item.id}>{formatCompetence(item)}</option>)}</select></label><label className="field-label">Comparação final<select value={filters.comparisonEnd} onChange={(event) => updateFilter("comparisonEnd", event.target.value)}><option value="">Selecione</option>{options.competencias.map((item) => <option key={item.id} value={item.id}>{formatCompetence(item)}</option>)}</select></label></div>}
        </form>
      </section>

      {error && <div className="request-feedback request-feedback--error dashboard-error" role="alert"><AlertCircle size={18} /><p>{error}</p></div>}
      {analysis && <>
        {analysis.qualidade.competencias_sem_dados.length > 0 && <div className="analytics-data-warning"><AlertCircle size={18} /><span><strong>Período com dados incompletos.</strong> {analysis.qualidade.competencias_com_dados} de {analysis.qualidade.competencias_no_periodo} competências possuem movimentações concluídas para todas as {analysis.qualidade.ups_esperadas} UPS esperadas. Meses incompletos não entram na média.</span></div>}
        {!analysis.resumo.estoque_final_completo && <div className="analytics-data-warning"><AlertCircle size={18} /><span><strong>Cobertura indisponível.</strong> A competência final não possui estoque concluído para todas as UPS selecionadas. Consumo e média continuam disponíveis.</span></div>}

        <section className="analytics-summary-grid">
          <SummaryCard label="Consumo total" value={formatDecimal(analysis.resumo.consumo_total)} helper="Somente saídas" />
          <SummaryCard label="Média mensal" value={formatDecimal(analysis.resumo.media_mensal)} helper={`${analysis.qualidade.competencias_com_dados} competência(s) com dados`} />
          <SummaryCard label="Medicamentos consumidos" value={analysis.resumo.medicamentos_com_consumo} helper={`${analysis.resumo.medicamentos_sem_consumo} sem saída`} />
          <SummaryCard label="Maior consumo" value={analysis.resumo.maior_consumo ? formatDecimal(analysis.resumo.maior_consumo.consumo) : "0"} helper={analysis.resumo.maior_consumo?.descricao || "Sem consumo no período"} />
        </section>

        <section className="analytics-panel analytics-medicine-focus">
          <div className="analytics-panel__heading analytics-panel__heading--actions"><div><h2>Média por medicamento</h2><p>Selecione um medicamento para acompanhar o consumo dentro do período e dos filtros aplicados.</p></div><label className="field-label analytics-medicine-select">Medicamento<select value={selectedMedicine ? String(selectedMedicine.id) : ""} onChange={(event) => setSelectedMedicineId(event.target.value)} disabled={!medicines.length}>{medicines.map((item) => <option key={item.id} value={item.id}>{item.descricao} · {item.codigo_gmus}</option>)}</select></label></div>
          {selectedMedicine ? <><div className="analytics-summary-grid analytics-medicine-summary"><SummaryCard label="Consumo no período" value={formatDecimal(selectedMedicine.consumo)} helper="Somente saídas" /><SummaryCard label="Média mensal do período" value={formatDecimal(selectedMedicine.media_mensal)} helper="Inclui meses completos sem saída" /><SummaryCard label="Média nos meses com saída" value={formatDecimal(selectedMedicine.media_meses_com_consumo)} helper={`${selectedMedicine.meses_com_consumo} mês(es) com consumo`} /><SummaryCard label="Estoque atual" value={selectedMedicine.estoque_atual === null ? "Sem base" : formatDecimal(selectedMedicine.estoque_atual)} helper={formatCompetence(analysis.periodo.final)} /><SummaryCard label="Cobertura estimada" value={selectedMedicine.dias_cobertura === null ? "Sem base" : `${Math.round(Number(selectedMedicine.dias_cobertura))} dias`} helper={selectedMedicine.classe_abc ? `Classe ${selectedMedicine.classe_abc} · tendência ${selectedMedicine.tendencia}` : "Sem consumo"} /></div><div className="analytics-medicine-chart"><ConsumptionEvolutionChart data={selectedMedicine.evolucao || []} /></div></> : <p className="analytics-empty">Nenhum medicamento encontrado com os filtros atuais.</p>}
        </section>

        {comparison && <section className="analytics-panel analytics-comparison"><div><span>Período atual</span><strong>{formatDecimal(analysis.resumo.consumo_total)}</strong></div><div><span>Período comparado</span><strong>{formatDecimal(comparison.resumo.consumo_total)}</strong></div><div className={Number(variation) > 0 ? "comparison-change comparison-change--up" : "comparison-change comparison-change--down"}>{Number(variation) > 0 ? <TrendingUp size={22} /> : <TrendingDown size={22} />}<span>Variação<strong>{percentage(variation)}</strong></span></div></section>}

        <div className="analytics-chart-grid">
          <section className="analytics-panel"><div className="analytics-panel__heading"><TrendingUp size={21} /><div><h2>Evolução mensal</h2><p>Saídas por competência no período selecionado.</p></div></div><ConsumptionEvolutionChart data={analysis.evolucao} /></section>
          <section className="analytics-panel"><div className="analytics-panel__heading"><BarChart3 size={21} /><div><h2>Medicamentos com maior saída</h2><p>Ranking dos dez maiores consumos.</p></div></div><HorizontalBarChart data={analysis.ranking.slice(0, 10)} emptyMessage="Nenhuma saída encontrada no período." /></section>
        </div>

        <section className="analytics-panel"><div className="analytics-panel__heading"><BarChart3 size={21} /><div><h2>Consumo por UPS</h2><p>As unidades permanecem separadas para preservar a origem dos dados.</p></div></div><HorizontalBarChart data={analysis.por_ups} labelKey="nome" emptyMessage="Nenhuma UPS possui saída no período." /></section>

        <div className="analytics-chart-grid">
          <section className="analytics-panel"><div className="analytics-panel__heading"><BarChart3 size={21} /><div><h2>Curva ABC</h2><p>Distribuição dos medicamentos conforme sua participação acumulada no consumo.</p></div></div><HorizontalBarChart data={analysis.curva_abc} labelKey="classe" emptyMessage="Não há consumo suficiente para calcular a curva ABC." /></section>
          <section className="analytics-panel"><div className="analytics-panel__heading"><AlertCircle size={21} /><div><h2>Menor cobertura estimada</h2><p>Medicamentos com menor número de dias de estoque, considerando a média mensal.</p></div></div>{lowCoverage.length ? <ol className="analytics-coverage-list">{lowCoverage.map((item) => <li key={item.id}><span><strong>{item.descricao}</strong><small>{item.codigo_gmus} · classe {item.classe_abc}</small></span><b>{Math.round(Number(item.dias_cobertura))} dias</b></li>)}</ol> : <p className="analytics-empty">Importe o estoque final completo para calcular a cobertura.</p>}</section>
        </div>

        <section className="analytics-movement-context"><SummaryCard label="Entradas operacionais" value={formatDecimal(analysis.resumo.entradas_total)} helper="Compras, transferências e acertos" /><SummaryCard label="Saídas operacionais" value={formatDecimal(analysis.resumo.saidas_operacionais_total)} helper="Consumo e demais saídas" /><SummaryCard label="Saldo das movimentações" value={formatDecimal(analysis.resumo.saldo_movimentacoes)} helper="Entradas menos saídas operacionais" /></section>

        <section className="analytics-panel analytics-ranking-panel">
          <div className="analytics-panel__heading analytics-panel__heading--actions"><div><h2>Ranking completo</h2><p>Média, cobertura, tendência e participação no período.</p></div><div className="analytics-ranking-actions"><label className="field-label">Ordenar por<select value={rankingOrder} onChange={(event) => setRankingOrder(event.target.value)}><option value="consumo">Maior consumo</option><option value="media">Maior média</option><option value="cobertura">Menor cobertura</option><option value="tendencia">Maior crescimento</option></select></label><button type="button" className="secondary-button" onClick={() => exportRanking(analysis)} disabled={!analysis.ranking.length}><Download size={17} />Exportar CSV</button></div></div>
          <div className="analysis-table-wrapper"><table className="analysis-table analytics-ranking-table"><thead><tr><th>#</th><th>Medicamento</th><th>ABC</th><th>Consumo</th><th>Média mensal</th><th>Estoque</th><th>Cobertura</th><th>Tendência</th><th>Participação</th></tr></thead><tbody>{orderedRanking.map((item, index) => <tr key={item.id}><td>{index + 1}</td><td><strong>{item.descricao}</strong><small>{item.codigo_gmus} · {item.unidade || "sem unidade"}</small></td><td><span className={`analytics-abc analytics-abc--${item.classe_abc?.toLowerCase() || "none"}`}>{item.classe_abc || "—"}</span></td><td>{formatDecimal(item.consumo)}</td><td>{formatDecimal(item.media_mensal)}</td><td>{item.estoque_atual === null ? "—" : formatDecimal(item.estoque_atual)}</td><td>{item.dias_cobertura === null ? "—" : `${Math.round(Number(item.dias_cobertura))} dias`}</td><td>{item.tendencia === "sem_base" ? "Sem base" : item.tendencia}</td><td>{percentage(item.participacao_percentual)}</td></tr>)}</tbody></table>{!analysis.ranking.length && <p className="analytics-empty">Nenhum medicamento apresentou saída no período.</p>}</div>
        </section>

        <details className="analytics-panel analytics-no-consumption"><summary>Medicamentos sem saída no período <span>{analysis.sem_consumo.length}</span></summary>{analysis.sem_consumo.length ? <ul>{analysis.sem_consumo.map((item) => <li key={item.id}><span><strong>{item.descricao}</strong><small>{item.codigo_gmus}</small></span><span>{item.unidade || "Sem unidade"}</span></li>)}</ul> : <p className="analytics-empty">Todos os medicamentos presentes nos relatórios tiveram saída.</p>}</details>
      </>}
    </main>
  );
}

export default AnalisesPage;
