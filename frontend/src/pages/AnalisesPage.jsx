import {
  AlertCircle,
  BarChart3,
  Building2,
  CalendarRange,
  Gauge,
  LoaderCircle,
  PackageX,
  PieChart,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import { getAnalysisOptions, getConsumptionAnalysis } from "../api/analysis";
import { ConsumptionEvolutionChart, HorizontalBarChart } from "../components/analysis/ConsumptionCharts";
import FilterSelect from "../components/filters/FilterSelect";
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

function AnalisesPage() {
  const [options, setOptions] = useState({ competencias: [], ups: [], subgrupos: [], classificacoes: [], unidades: [] });
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters);
  const [analysis, setAnalysis] = useState(null);
  const [selectedMedicineId, setSelectedMedicineId] = useState("");
  const [rankingOrder, setRankingOrder] = useState("consumo");
  const [abcFilter, setAbcFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  async function loadAnalysis(nextFilters) {
    if (!nextFilters.competenceStart || !nextFilters.competenceEnd) return;
    setIsAnalyzing(true);
    setError("");
    try {
      setAnalysis(await getConsumptionAnalysis(nextFilters));
      setAppliedFilters(nextFilters);
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
  const filteredRanking = useMemo(
    () => orderedRanking.filter((item) => !abcFilter || item.classe_abc === abcFilter),
    [abcFilter, orderedRanking],
  );
  const lowCoverage = useMemo(
    () => analysis ? analysis.ranking.filter((item) => Number(item.dias_cobertura) > 0).sort((a, b) => Number(a.dias_cobertura) - Number(b.dias_cobertura)).slice(0, 10) : [],
    [analysis],
  );
  const evolutionHighlights = useMemo(() => {
    const items = analysis?.evolucao?.filter((item) => item.tem_dados) || [];
    if (!items.length) return null;
    const highest = items.reduce((current, item) => Number(item.consumo) > Number(current.consumo) ? item : current);
    const lowest = items.reduce((current, item) => Number(item.consumo) < Number(current.consumo) ? item : current);
    const first = items[0];
    const last = items[items.length - 1];
    return {
      highest,
      lowest,
      variation: Number(last.consumo) - Number(first.consumo),
      first,
      last,
    };
  }, [analysis]);
  const appliedFilterSummary = useMemo(() => {
    const start = options.competencias.find((item) => String(item.id) === String(appliedFilters.competenceStart));
    const end = options.competencias.find((item) => String(item.id) === String(appliedFilters.competenceEnd));
    const ups = options.ups.find((item) => String(item.id) === String(appliedFilters.upsId));
    const category = categories.find((item) => item.value === appliedFilters.category);
    const values = [
      start && end ? `${formatCompetence(start)} a ${formatCompetence(end)}` : null,
      ups ? ups.nome : "Todas as UPS",
      category ? category.label : "Todas as categorias",
      appliedFilters.unit || "Todas as unidades",
    ];
    if (appliedFilters.search.trim()) values.push(`Busca: ${appliedFilters.search.trim()}`);
    return values;
  }, [appliedFilters, categories, options.competencias, options.ups]);

  return (
    <main className="analytics-page">
      <header className="page-heading"><div><span className="eyebrow">Inteligência de estoque</span><h1>Análise de consumo</h1><p>Consumo corresponde somente às saídas registradas no relatório de movimentações.</p></div></header>

      <section className="analytics-panel analytics-filter-panel">
        <div className="analytics-panel__heading"><CalendarRange size={21} /><div><h2>Período e filtros</h2><p>A média considera apenas competências com relatório de movimentação.</p></div></div>
        <form className="analytics-filters" onSubmit={submit}>
          <FilterSelect
            id="analysis-competence-start"
            label="Competência inicial"
            value={filters.competenceStart}
            options={options.competencias.map((item) => ({ value: item.id, label: formatCompetence(item) }))}
            placeholder="Selecione"
            isLoading={isLoading}
            onChange={(value) => updateFilter("competenceStart", value)}
            allowEmpty={false}
          />
          <FilterSelect
            id="analysis-competence-end"
            label="Competência final"
            value={filters.competenceEnd}
            options={options.competencias.map((item) => ({ value: item.id, label: formatCompetence(item) }))}
            placeholder="Selecione"
            isLoading={isLoading}
            onChange={(value) => updateFilter("competenceEnd", value)}
            allowEmpty={false}
          />
          <FilterSelect
            id="analysis-ups"
            label="UPS"
            value={filters.upsId}
            options={options.ups.map((item) => ({ value: item.id, label: item.nome }))}
            placeholder="Todas as UPS"
            onChange={(value) => updateFilter("upsId", value)}
          />
          <FilterSelect
            id="analysis-category"
            label="Categoria"
            value={filters.category}
            options={categories}
            placeholder="Todas as categorias"
            onChange={(value) => updateFilter("category", value)}
          />
          <FilterSelect
            id="analysis-unit"
            label="Unidade"
            value={filters.unit}
            options={options.unidades.map((item) => ({ value: item, label: item }))}
            placeholder="Todas as unidades"
            onChange={(value) => updateFilter("unit", value)}
          />
          <label className="field-label analytics-search">Medicamento<span><Search size={17} /><input value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="Nome ou código G-MUS" /></span></label>
          <div className="analytics-filter-actions">
            <label className="analytics-comparison-toggle"><input type="checkbox" checked={filters.comparisonEnabled} onChange={(event) => updateFilter("comparisonEnabled", event.target.checked)} />Comparar com outro período</label>
            <button className="secondary-button analytics-clear" type="button" onClick={clearFilters} disabled={isAnalyzing}>Limpar filtros</button>
            <button className="primary-button analytics-submit" type="submit" disabled={isAnalyzing || !filters.competenceStart || !filters.competenceEnd || (filters.comparisonEnabled && (!filters.comparisonStart || !filters.comparisonEnd))}>{isAnalyzing ? <LoaderCircle className="button-spinner" size={17} /> : <BarChart3 size={17} />}Analisar</button>
          </div>
          {filters.comparisonEnabled && (
            <div className="analytics-comparison-fields">
              <FilterSelect
                id="analysis-comparison-start"
                label="Comparação inicial"
                value={filters.comparisonStart}
                options={options.competencias.map((item) => ({ value: item.id, label: formatCompetence(item) }))}
                placeholder="Selecione"
                onChange={(value) => updateFilter("comparisonStart", value)}
              />
              <FilterSelect
                id="analysis-comparison-end"
                label="Comparação final"
                value={filters.comparisonEnd}
                options={options.competencias.map((item) => ({ value: item.id, label: formatCompetence(item) }))}
                placeholder="Selecione"
                onChange={(value) => updateFilter("comparisonEnd", value)}
              />
            </div>
          )}
        </form>
      </section>

      {error && <div className="request-feedback request-feedback--error dashboard-error" role="alert"><AlertCircle size={18} /><p>{error}</p></div>}
      {analysis && <>
        {analysis.qualidade.competencias_sem_dados.length > 0 && <div className="analytics-data-warning"><AlertCircle size={18} /><span><strong>Período com dados incompletos.</strong> {analysis.qualidade.competencias_com_dados} de {analysis.qualidade.competencias_no_periodo} competências possuem movimentações concluídas para todas as {analysis.qualidade.ups_esperadas} UPS esperadas. Meses incompletos não entram na média.</span></div>}
        {!analysis.resumo.estoque_final_completo && <div className="analytics-data-warning"><AlertCircle size={18} /><span><strong>Cobertura indisponível.</strong> A competência final não possui estoque concluído para todas as UPS selecionadas. Consumo e média continuam disponíveis.</span></div>}

        <section className="analytics-panel analytics-summary-panel">
          <div className="analytics-panel__heading">
            <BarChart3 size={21} />
            <div>
              <h2>Resumo do período</h2>
              <p>Indicadores essenciais para uma leitura rápida do consumo.</p>
              <small className="analytics-filter-summary">Filtros aplicados: {appliedFilterSummary.join(" · ")}</small>
            </div>
          </div>
          <div className="analytics-summary-grid">
            <SummaryCard label="Consumo total" value={formatDecimal(analysis.resumo.consumo_total)} helper="Somente saídas" />
            <SummaryCard label="Média mensal" value={formatDecimal(analysis.resumo.media_mensal)} helper={`${analysis.qualidade.competencias_com_dados} competência(s) com dados`} />
            <SummaryCard label="Medicamentos consumidos" value={analysis.resumo.medicamentos_com_consumo} helper={`${analysis.resumo.medicamentos_sem_consumo} sem saída`} />
            <SummaryCard label="Maior consumo" value={analysis.resumo.maior_consumo ? formatDecimal(analysis.resumo.maior_consumo.consumo) : "0"} helper={analysis.resumo.maior_consumo?.descricao || "Sem consumo no período"} />
          </div>
        </section>

        <section className="analytics-panel analytics-medicine-focus">
          <div className="analytics-panel__heading analytics-panel__heading--actions"><div><h2>Média por medicamento</h2><p>Selecione um medicamento para acompanhar o consumo dentro do período e dos filtros aplicados.</p></div><FilterSelect id="analysis-medicine" label="Medicamento" className="analytics-medicine-select" value={selectedMedicine ? String(selectedMedicine.id) : ""} options={medicines.map((item) => ({ value: item.id, label: `${item.descricao} · ${item.codigo_gmus}` }))} placeholder="Selecione um medicamento" onChange={setSelectedMedicineId} /> </div>
          {selectedMedicine ? <><div className="analytics-summary-grid analytics-medicine-summary"><SummaryCard label="Consumo no período" value={formatDecimal(selectedMedicine.consumo)} helper="Somente saídas" /><SummaryCard label="Média mensal do período" value={formatDecimal(selectedMedicine.media_mensal)} helper="Inclui meses completos sem saída" /><SummaryCard label="Média nos meses com saída" value={formatDecimal(selectedMedicine.media_meses_com_consumo)} helper={`${selectedMedicine.meses_com_consumo} mês(es) com consumo`} /><SummaryCard label="Estoque atual" value={selectedMedicine.estoque_atual === null ? "Sem base" : formatDecimal(selectedMedicine.estoque_atual)} helper={formatCompetence(analysis.periodo.final)} /><SummaryCard label="Cobertura estimada" value={selectedMedicine.dias_cobertura === null ? "Sem base" : `${Math.round(Number(selectedMedicine.dias_cobertura))} dias`} helper={selectedMedicine.classe_abc ? `Classe ${selectedMedicine.classe_abc} · tendência ${selectedMedicine.tendencia}` : "Sem consumo"} /></div><div className="analytics-medicine-chart"><ConsumptionEvolutionChart data={selectedMedicine.evolucao || []} /></div></> : <p className="analytics-empty">Nenhum medicamento encontrado com os filtros atuais.</p>}
        </section>

        {comparison && <section className="analytics-panel analytics-comparison"><div><span>Período atual</span><strong>{formatDecimal(analysis.resumo.consumo_total)}</strong></div><div><span>Período comparado</span><strong>{formatDecimal(comparison.resumo.consumo_total)}</strong></div><div className={Number(variation) > 0 ? "comparison-change comparison-change--up" : "comparison-change comparison-change--down"}>{Number(variation) > 0 ? <TrendingUp size={22} /> : <TrendingDown size={22} />}<span>Variação<strong>{percentage(variation)}</strong></span></div></section>}

        <details className="analytics-disclosure">
          <summary>
            <span><TrendingUp size={19} />Evolução e maiores consumos</span>
            <small>Curva mensal e ranking principal</small>
          </summary>
          <div className="analytics-disclosure__content">
            <div className="analytics-chart-grid">
              <section className="analytics-panel"><div className="analytics-panel__heading"><CalendarRange size={21} /><div><h2>Evolução mensal</h2><p>Saídas por competência no período selecionado.</p></div></div><ConsumptionEvolutionChart data={analysis.evolucao} />{evolutionHighlights && <div className="analytics-chart-highlights"><div><small>Maior saída</small><strong>{formatDecimal(evolutionHighlights.highest.consumo)}</strong><span>{formatCompetence(evolutionHighlights.highest.competencia)}</span></div><div><small>Menor saída</small><strong>{formatDecimal(evolutionHighlights.lowest.consumo)}</strong><span>{formatCompetence(evolutionHighlights.lowest.competencia)}</span></div><div><small>Variação no período</small><strong>{evolutionHighlights.variation > 0 ? "+" : ""}{formatDecimal(evolutionHighlights.variation)}</strong><span>{formatCompetence(evolutionHighlights.first.competencia)} a {formatCompetence(evolutionHighlights.last.competencia)}</span></div></div>}</section>
              <section className="analytics-panel"><div className="analytics-panel__heading"><BarChart3 size={21} /><div><h2>Medicamentos com maior saída</h2><p>Ranking dos dez maiores consumos.</p></div></div><HorizontalBarChart data={analysis.ranking.slice(0, 10)} emptyMessage="Nenhuma saída encontrada no período." /></section>
            </div>
          </div>
        </details>

        <details className="analytics-disclosure">
          <summary>
            <span><BarChart3 size={19} />Indicadores avançados</span>
            <small>UPS, curva ABC, cobertura e detalhamento</small>
          </summary>
          <div className="analytics-disclosure__content">
            <section className="analytics-panel"><div className="analytics-panel__heading"><Building2 size={21} /><div><h2>Consumo por UPS</h2><p>As unidades permanecem separadas para preservar a origem dos dados.</p></div></div><HorizontalBarChart data={analysis.por_ups} labelKey="nome" emptyMessage="Nenhuma UPS possui saída no período." /></section>

            <section className="analytics-panel analytics-abc-panel"><div className="analytics-panel__heading"><PieChart size={21} /><div><h2>Curva ABC</h2><p>Distribuição dos medicamentos conforme sua participação acumulada no consumo.</p></div></div><HorizontalBarChart data={analysis.curva_abc} labelKey="classe" emptyMessage="Não há consumo suficiente para calcular a curva ABC." /></section>

            <section className="analytics-panel analytics-coverage-panel"><div className="analytics-panel__heading"><Gauge size={22} strokeWidth={2.5} /><div><h2>Menor cobertura positiva</h2><p>Medicamentos com menor número de dias de estoque, entre os que possuem cobertura maior que zero.</p></div></div>{lowCoverage.length ? <ol className="analytics-coverage-list">{lowCoverage.map((item) => <li key={item.id}><span><strong>{item.descricao}</strong><small>{item.codigo_gmus} · classe {item.classe_abc}</small></span><b>{Math.round(Number(item.dias_cobertura))} dias</b></li>)}</ol> : <p className="analytics-empty">Nenhum medicamento possui cobertura positiva no período.</p>}</section>

            <section className="analytics-movement-context"><SummaryCard label="Entradas operacionais" value={formatDecimal(analysis.resumo.entradas_total)} helper="Compras, transferências e acertos" /><SummaryCard label="Saídas operacionais" value={formatDecimal(analysis.resumo.saidas_operacionais_total)} helper="Consumo e demais saídas" /><SummaryCard label="Saldo das movimentações" value={formatDecimal(analysis.resumo.saldo_movimentacoes)} helper="Entradas menos saídas operacionais" /></section>

            <details className="analytics-panel analytics-ranking-panel analytics-ranking-disclosure">
          <summary><span><BarChart3 size={19} />Ranking completo</span><small>Filtros, consumo e indicadores por medicamento</small></summary>
          <div className="analytics-ranking-disclosure__content">
          <div className="analytics-ranking-toolbar">
            <div className="analytics-ranking-explainer"><strong>Como funciona a classificação ABC</strong><p>A classe A reúne os medicamentos com maior participação no consumo, B representa a faixa intermediária e C concentra os menores consumos. Use os blocos abaixo para abrir somente a classe que deseja analisar.</p></div>
            <div className="analytics-ranking-controls"><div className="analytics-ranking-actions"><FilterSelect id="analysis-abc-filter" label="Classe ABC" value={abcFilter} options={[{ value: "A", label: "Classe A" }, { value: "B", label: "Classe B" }, { value: "C", label: "Classe C" }]} placeholder="Todas as classes" onChange={setAbcFilter} /><FilterSelect id="analysis-ranking-order" label="Ordenar por" value={rankingOrder} options={[{ value: "consumo", label: "Maior consumo" }, { value: "media", label: "Maior média" }, { value: "cobertura", label: "Menor cobertura" }, { value: "tendencia", label: "Maior crescimento" }]} placeholder="Ordenar" allowEmpty={false} onChange={setRankingOrder} /></div></div>
          </div>
          <div className="analysis-table-wrapper"><table className="analysis-table analytics-ranking-table"><thead><tr><th>#</th><th>Medicamento</th><th>ABC</th><th>Consumo</th><th>Média mensal</th><th>Estoque</th><th>Cobertura</th><th>Tendência</th><th>Participação</th></tr></thead><tbody>{filteredRanking.map((item, index) => <tr key={item.id}><td>{index + 1}</td><td><strong>{item.descricao}</strong><small>{item.codigo_gmus} · {item.unidade || "sem unidade"}</small></td><td><span className={`analytics-abc analytics-abc--${item.classe_abc?.toLowerCase() || "none"}`}>{item.classe_abc || "—"}</span></td><td>{formatDecimal(item.consumo)}</td><td>{formatDecimal(item.media_mensal)}</td><td>{item.estoque_atual === null ? "—" : formatDecimal(item.estoque_atual)}</td><td>{item.dias_cobertura === null ? "—" : `${Math.round(Number(item.dias_cobertura))} dias`}</td><td>{item.tendencia === "sem_base" ? "Sem base" : item.tendencia}</td><td>{percentage(item.participacao_percentual)}</td></tr>)}</tbody></table>{!filteredRanking.length && <p className="analytics-empty">Nenhum medicamento corresponde aos filtros do ranking.</p>}</div>
          </div>
            </details>

            <details className="analytics-panel analytics-no-consumption"><summary><span><PackageX size={19} />Medicamentos sem saída no período</span><strong>{analysis.sem_consumo.length}</strong></summary>{analysis.sem_consumo.length ? <ul>{analysis.sem_consumo.map((item) => <li key={item.id}><span><strong>{item.descricao}</strong><small>{item.codigo_gmus}</small></span><span>{item.unidade || "Sem unidade"}</span></li>)}</ul> : <p className="analytics-empty">Todos os medicamentos presentes nos relatórios tiveram saída.</p>}</details>
          </div>
        </details>
      </>}
    </main>
  );
}

export default AnalisesPage;
