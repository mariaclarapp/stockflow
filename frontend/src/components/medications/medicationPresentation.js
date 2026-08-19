export function stockQuantityText(quantity) {
  if (quantity === null || quantity === undefined) return "Não informado";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}
