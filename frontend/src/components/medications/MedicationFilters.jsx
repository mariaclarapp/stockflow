import { CalendarDays, MapPin, Search, SlidersHorizontal, Tags, X } from "lucide-react";

import FilterSelect from "../filters/FilterSelect";
import CategorySelect from "./CategorySelect";

function MedicationFilters({
  searchInput, categoryValue, tagValue, competenceId, defaultCompetenceId, upsId, unit,
  stockStatus, validationStatus, ordering, classifications, subgroups,
  competencies, upsOptions, units, isLoading, isLoadingCategories,
  onSearchInputChange, onSearch, onCategoryChange, onTagChange, onCompetenceChange,
  onUpsChange, onUnitChange, onStockStatusChange, onValidationStatusChange,
  onOrderingChange, onClearSearch, onClearFilters,
}) {
  const hasFilters = Boolean(
    searchInput || categoryValue || tagValue || competenceId !== defaultCompetenceId || upsId
    || unit || stockStatus || validationStatus || ordering !== "descricao",
  );

  return (
    <form className="medication-filters" onSubmit={onSearch}>
      <fieldset className="medication-filter-group medication-filter-group--search">
        <legend>Busca</legend>
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
              <button type="button" className="medication-search__clear" onClick={onClearSearch} aria-label="Limpar pesquisa" title="Limpar pesquisa">
                <X size={16} />
              </button>
            )}
          </div>
        </div>
      </fieldset>

      <fieldset className="medication-filter-group">
        <legend>Contexto do estoque</legend>
        <div className="medication-filter-group__grid medication-filter-group__grid--context">
          <CategorySelect value={categoryValue} subgroups={subgroups} classifications={classifications} isLoading={isLoadingCategories} onChange={onCategoryChange} />
          <FilterSelect
            id="medication-tag"
            label="Tags"
            value={tagValue}
            options={classifications.filter((item) => item.ativo).map((item) => ({ value: item.id, label: item.nome }))}
            placeholder="Todas as tags"
            icon={Tags}
            isLoading={isLoadingCategories}
            onChange={onTagChange}
          />
          <FilterSelect
            id="medication-competence"
            label="Competência"
            value={competenceId}
            options={competencies.map((item) => ({ value: item.id, label: `${String(item.mes).padStart(2, "0")}/${item.ano}` }))}
            placeholder={competencies.length ? "Todas as competências" : "Sem competência"}
            icon={CalendarDays}
            isLoading={isLoadingCategories}
            onChange={onCompetenceChange}
          />
          <FilterSelect
            id="medication-ups"
            label="UPS"
            value={upsId}
            options={upsOptions.map((item) => ({ value: item.id, label: item.nome }))}
            placeholder="Todas as UPS"
            icon={MapPin}
            onChange={onUpsChange}
          />
        </div>
      </fieldset>

      <fieldset className="medication-filter-group">
        <legend>Refinamento da lista</legend>
        <div className="medication-filter-group__grid medication-filter-group__grid--refinement">
          <FilterSelect id="medication-unit" label="Unidade" value={unit} options={units.map((item) => ({ value: item, label: item }))} placeholder="Todas" onChange={onUnitChange} />
          <FilterSelect
            id="medication-stock-status"
            label="Situação"
            value={stockStatus}
            options={[{ value: "disponivel", label: "Com estoque" }, { value: "sem_estoque", label: "Sem estoque" }]}
            placeholder="Todas"
            onChange={onStockStatusChange}
          />
          <FilterSelect
            id="medication-ordering"
            label="Ordenar por"
            value={ordering}
            options={[{ value: "descricao", label: "Nome" }, { value: "codigo", label: "Código G-MUS" }, { value: "maior_estoque", label: "Maior estoque" }, { value: "menor_estoque", label: "Menor estoque" }]}
            placeholder="Nome"
            onChange={onOrderingChange}
            allowEmpty={false}
          />
          <FilterSelect
            id="medication-validation"
            label="Validação"
            value={validationStatus}
            options={[{ value: "validado", label: "Validados" }, { value: "divergente", label: "Divergentes" }, { value: "nao_validado", label: "Não validados" }]}
            placeholder="Todas"
            onChange={onValidationStatusChange}
          />
        </div>
      </fieldset>

      <div className="medication-filter-actions">
        <button type="button" className="medication-clear-filters" onClick={onClearFilters} disabled={isLoading || !hasFilters}>Limpar filtros</button>
        <button type="submit" className="primary-button medication-search-button" disabled={isLoading}>
          <SlidersHorizontal size={17} />
          Aplicar filtros
        </button>
      </div>
    </form>
  );
}

export default MedicationFilters;
