import FilterSelect from "../filters/FilterSelect";

function subgroupLabel(subgroup) {
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Subgrupo sem identificação");
}

function SubgroupSelect({ value, subgroups, isLoading, onChange }) {
  return (
    <FilterSelect
      id="medication-subgroup"
      className="medication-subgroup-filter"
      label="Subgrupo G-MUS"
      value={value}
      options={subgroups.map((subgroup) => ({
        value: String(subgroup.id),
        label: subgroupLabel(subgroup),
      }))}
      placeholder="Todos os subgrupos"
      loadingLabel="Carregando subgrupos..."
      isLoading={isLoading}
      onChange={onChange}
    />
  );
}

export default SubgroupSelect;
