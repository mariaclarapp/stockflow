import { Search, SlidersHorizontal, X } from "lucide-react";

import CategorySelect from "./CategorySelect";

function MedicationFilters({
  searchInput,
  categoryValue,
  competenceId,
  defaultCompetenceId,
  upsId,
  unit,
  stockStatus,
  ordering,
  classifications,
  subgroups,
  competencies,
  upsOptions,
  units,
  isLoading,
  isLoadingCategories,
  onSearchInputChange,
  onSearch,
  onCategoryChange,
  onCompetenceChange,
  onUpsChange,
  onUnitChange,
  onStockStatusChange,
  onOrderingChange,
  onClearSearch,
  onClearFilters,
}) {
  const hasFilters = Boolean(
    searchInput
    || categoryValue
    || competenceId !== defaultCompetenceId
    || upsId
    || unit
    || stockStatus
    || ordering !== "descricao",
  );

  return (
    <form className="medication-filters" onSubmit={onSearch}>
      <div className="medication-search">
        <label htmlFor="medication-search">Pesquisar medicamentos</label>
        <div className="medication-search__control">
          <Search size={18} aria-hidden="true" />
          <input
            id="medication-search"
            type="text"
            value={searchInput}
            onChange={(event) => onSearchInputChange(event.target.value)}
            placeholder="Buscar por medicamento ou código G-MUS"
            autoComplete="off"
          />
          {searchInput && (
            <button
              type="button"
              className="medication-search__clear"
              onClick={onClearSearch}
              aria-label="Limpar pesquisa"
              title="Limpar pesquisa"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <CategorySelect
        value={categoryValue}
        subgroups={subgroups}
        classifications={classifications}
        isLoading={isLoadingCategories}
        onChange={onCategoryChange}
      />

      <label className="medication-filter-field">
        <span>Competência</span>
        <select
          value={competenceId}
          onChange={(event) => onCompetenceChange(event.target.value)}
          disabled={isLoadingCategories}
        >
          {!competencies.length && <option value="">Sem competência</option>}
          {competencies.map((item) => (
            <option key={item.id} value={item.id}>
              {String(item.mes).padStart(2, "0")}/{item.ano}
            </option>
          ))}
        </select>
      </label>

      <label className="medication-filter-field">
        <span>UPS</span>
        <select value={upsId} onChange={(event) => onUpsChange(event.target.value)}>
          <option value="">Todas as UPS</option>
          {upsOptions.map((item) => (
            <option key={item.id} value={item.id}>{item.nome}</option>
          ))}
        </select>
      </label>

      <label className="medication-filter-field">
        <span>Unidade</span>
        <select value={unit} onChange={(event) => onUnitChange(event.target.value)}>
          <option value="">Todas</option>
          {units.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>

      <label className="medication-filter-field">
        <span>Situação</span>
        <select
          value={stockStatus}
          onChange={(event) => onStockStatusChange(event.target.value)}
        >
          <option value="">Todas</option>
          <option value="disponivel">Com estoque</option>
          <option value="sem_estoque">Sem estoque</option>
          <option value="sem_dados">Sem dados</option>
        </select>
      </label>

      <label className="medication-filter-field">
        <span>Ordenar por</span>
        <select value={ordering} onChange={(event) => onOrderingChange(event.target.value)}>
          <option value="descricao">Nome</option>
          <option value="codigo">Código G-MUS</option>
          <option value="maior_estoque">Maior estoque</option>
          <option value="menor_estoque">Menor estoque</option>
        </select>
      </label>

      <button
        type="button"
        className="medication-clear-filters"
        onClick={onClearFilters}
        disabled={isLoading || !hasFilters}
      >
        Limpar filtros
      </button>

      <button
        type="submit"
        className="primary-button medication-search-button"
        disabled={isLoading}
      >
        <SlidersHorizontal size={17} />
        Aplicar
      </button>
    </form>
  );
}

export default MedicationFilters;
