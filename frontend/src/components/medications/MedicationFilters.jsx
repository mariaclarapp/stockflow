import { Search, X } from "lucide-react";

import SubgroupSelect from "./SubgroupSelect";

function MedicationFilters({
  searchInput,
  subgroupId,
  subgroups,
  isLoading,
  isLoadingSubgroups,
  onSearchInputChange,
  onSearch,
  onSubgroupChange,
  onClearSearch,
  onClearFilters,
}) {
  const hasFilters = Boolean(searchInput || subgroupId);

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

      <SubgroupSelect
        value={subgroupId}
        subgroups={subgroups}
        isLoading={isLoadingSubgroups}
        onChange={onSubgroupChange}
      />

      <button
        type="submit"
        className="primary-button medication-search-button"
        disabled={isLoading}
      >
        <Search size={17} />
        Buscar
      </button>

      {hasFilters && (
        <button
          type="button"
          className="medication-clear-filters"
          onClick={onClearFilters}
          disabled={isLoading}
        >
          Limpar filtros
        </button>
      )}
    </form>
  );
}

export default MedicationFilters;
