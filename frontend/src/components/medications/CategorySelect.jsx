import { Tags } from "lucide-react";

import FilterSelect from "../filters/FilterSelect";

function subgroupLabel(subgroup) {
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Subgrupo sem nome");
}

function CategorySelect({ value, subgroups, classifications, isLoading, onChange }) {
  const commonClassifications = classifications.filter(
    (item) => item.ativo && item.nome?.toUpperCase() !== "MANIPULADO",
  );
  const manipulated = classifications.filter(
    (item) => item.ativo && item.nome?.toUpperCase() === "MANIPULADO",
  );
  const options = [
    ...subgroups.map((subgroup) => ({
      value: `subgrupo:${subgroup.id}`,
      label: subgroupLabel(subgroup),
      group: "Subgrupos G-MUS",
    })),
    ...commonClassifications.map((classification) => ({
      value: `classificacao:${classification.id}`,
      label: classification.nome,
      group: "Categorias StockFlow",
    })),
    ...manipulated.map((classification) => ({
      value: `classificacao:${classification.id}`,
      label: classification.nome,
      group: "Tags especiais",
    })),
  ];

  return (
    <FilterSelect
      id="medication-category"
      className="medication-category-select"
      label="Categoria"
      value={value}
      options={options}
      placeholder="Todas as categorias"
      loadingLabel="Carregando categorias..."
      isLoading={isLoading}
      icon={Tags}
      onChange={onChange}
    />
  );
}

export default CategorySelect;
