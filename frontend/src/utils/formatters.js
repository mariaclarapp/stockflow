export function formatCompetence(competence) {
  if (!competence) return "";
  return `${String(competence.mes).padStart(2, "0")}/${competence.ano}`;
}

export function formatDecimal(value) {
  const match = String(value ?? "").match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) return String(value ?? "");
  const [, sign, integer, fraction] = match;
  const groupedInteger = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sign}${groupedInteger}${fraction ? `,${fraction}` : ""}`;
}

export function formatDate(dateValue) {
  if (!dateValue) return "";
  const match = String(dateValue).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return String(dateValue);
  return `${match[3]}/${match[2]}/${match[1]}`;
}
