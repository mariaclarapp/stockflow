import { formatDecimal } from "../../utils/formatters";

function competenceLabel(item) {
  return `${String(item.mes).padStart(2, "0")}/${item.ano}`;
}

export function ConsumptionEvolutionChart({ data }) {
  const width = 760;
  const height = 250;
  const padding = { top: 22, right: 18, bottom: 42, left: 58 };
  const values = data.map((item) => Number(item.consumo || 0));
  const maximum = Math.max(...values, 1);
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const points = values.map((value, index) => {
    const x = padding.left + (data.length === 1 ? plotWidth / 2 : (index * plotWidth) / (data.length - 1));
    const y = padding.top + plotHeight - (value / maximum) * plotHeight;
    return { x, y, value, item: data[index] };
  });

  if (!data.length) return <p className="analytics-empty">Não há competências no período selecionado.</p>;

  return (
    <div className="analytics-line-chart" role="img" aria-label="Evolução mensal do consumo">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
        {[0, 0.5, 1].map((ratio) => {
          const y = padding.top + plotHeight - ratio * plotHeight;
          return (
            <g key={ratio}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid-line" />
              <text x={padding.left - 10} y={y + 4} textAnchor="end" className="chart-axis-label">{formatDecimal(maximum * ratio)}</text>
            </g>
          );
        })}
        {points.length > 1 && <polyline points={points.map(({ x, y }) => `${x},${y}`).join(" ")} className="chart-line" />}
        {points.map(({ x, y, value, item }, index) => (
          <g key={item.competencia.id}>
            <circle cx={x} cy={y} r="5" className={item.tem_dados ? "chart-point" : "chart-point chart-point--missing"}>
              <title>{`${competenceLabel(item.competencia)}: ${item.tem_dados ? formatDecimal(value) : "sem relatório"}`}</title>
            </circle>
            {(data.length <= 8 || index % 2 === 0 || index === data.length - 1) && (
              <text x={x} y={height - 15} textAnchor="middle" className="chart-axis-label">{competenceLabel(item.competencia)}</text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

export function HorizontalBarChart({ data, valueKey = "consumo", labelKey = "descricao", emptyMessage }) {
  const maximum = Math.max(...data.map((item) => Number(item[valueKey] || 0)), 1);
  if (!data.length) return <p className="analytics-empty">{emptyMessage}</p>;
  return (
    <div className="analytics-bars">
      {data.map((item) => (
        <div className="analytics-bar" key={`${item.id}-${item[labelKey]}`}>
          <div className="analytics-bar__label"><span title={item[labelKey]}>{item[labelKey]}</span><strong>{formatDecimal(item[valueKey])}</strong></div>
          <div className="analytics-bar__track"><span style={{ width: `${Math.max((Number(item[valueKey]) / maximum) * 100, 1)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}
