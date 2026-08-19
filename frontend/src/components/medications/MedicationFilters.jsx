import { Search, X } from "lucide-react";

import CategorySelect from "./CategorySelect";

function MedicationFilters({
  searchInput,
  categoryValue,
  classifications,
  subgroups,
  isLoading,
  isLoadingCategories,
  onSearchInputChange,
  onSearch,
  onCategoryChange,
  onClearSearch,
  onClearFilters,
}) {
  const hasFilters = Boolean(searchInput || categoryValue);

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
