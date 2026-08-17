import { Search, X } from "lucide-react";
import { useRef } from "react";

function PublicMedicationSearch({ value, isLoading, onChange, onClear, onSubmit }) {
  const inputRef = useRef(null);

  function handleClear() {
    onClear();
    inputRef.current?.focus();
  }

  return (
    <form className="public-search" onSubmit={onSubmit} noValidate>
      <label htmlFor="public-medication-search">Nome do medicamento</label>
      <div className="public-search__row">
        <div className="public-search__control">
          <Search size={21} aria-hidden="true" />
          <input
            ref={inputRef}
            id="public-medication-search"
            type="text"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Digite o nome do medicamento"
            autoComplete="off"
          />
          {value && (
            <button
              className="public-search__clear"
              type="button"
              onClick={handleClear}
              aria-label="Limpar pesquisa"
            >
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
        <button className="primary-button public-search__button" type="submit" disabled={isLoading}>
          <Search size={18} aria-hidden="true" />
          {isLoading ? "Buscando..." : "Buscar"}
        </button>
      </div>
    </form>
  );
}

export default PublicMedicationSearch;
