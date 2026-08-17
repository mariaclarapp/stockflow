import { Check, ChevronDown, SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";

function subgroupLabel(subgroup) {
  if (subgroup.codigo_gmus && subgroup.nome) {
    return `${subgroup.codigo_gmus} - ${subgroup.nome}`;
  }
  return subgroup.nome || String(subgroup.codigo_gmus || "Subgrupo sem identificação");
}

function SubgroupSelect({ value, subgroups, isLoading, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const optionRefs = useRef([]);
  const selectedSubgroup = subgroups.find(
    (subgroup) => String(subgroup.id) === String(value),
  );

  useEffect(() => {
    function handleOutsideClick(event) {
      if (!rootRef.current?.contains(event.target)) setIsOpen(false);
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function openMenu() {
    setIsOpen(true);
    const selectedIndex = selectedSubgroup
      ? subgroups.findIndex((subgroup) => subgroup.id === selectedSubgroup.id) + 1
      : 0;
    requestAnimationFrame(() => optionRefs.current[selectedIndex]?.focus());
  }

  function selectOption(nextValue) {
    onChange(nextValue);
    setIsOpen(false);
    triggerRef.current?.focus();
  }

  function handleOptionKeyDown(event, index) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      optionRefs.current[Math.min(index + 1, subgroups.length)]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      optionRefs.current[Math.max(index - 1, 0)]?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      optionRefs.current[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      optionRefs.current[subgroups.length]?.focus();
    }
  }

  return (
    <div className="medication-subgroup-filter" ref={rootRef}>
      <span id="medication-subgroup-label">Subgrupo G-MUS</span>
      <button
        ref={triggerRef}
        type="button"
        className={`subgroup-select__trigger${isOpen ? " subgroup-select__trigger--open" : ""}`}
        aria-labelledby="medication-subgroup-label"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls="medication-subgroup-options"
        disabled={isLoading}
        onClick={() => (isOpen ? setIsOpen(false) : openMenu())}
      >
        <SlidersHorizontal size={17} aria-hidden="true" />
        <span>
          {isLoading
            ? "Carregando subgrupos..."
            : selectedSubgroup
              ? subgroupLabel(selectedSubgroup)
              : "Todos os subgrupos"}
        </span>
        <ChevronDown className="subgroup-select__chevron" size={17} aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          className="subgroup-select__options"
          id="medication-subgroup-options"
          role="listbox"
          aria-labelledby="medication-subgroup-label"
        >
          <button
            ref={(element) => {
              optionRefs.current[0] = element;
            }}
            type="button"
            role="option"
            aria-selected={!value}
            className={`subgroup-select__option${!value ? " subgroup-select__option--selected" : ""}`}
            onClick={() => selectOption("")}
            onKeyDown={(event) => handleOptionKeyDown(event, 0)}
          >
            <span className="subgroup-select__check">{!value && <Check size={15} />}</span>
            <span>Todos os subgrupos</span>
          </button>

          {subgroups.map((subgroup, index) => {
            const isSelected = String(subgroup.id) === String(value);
            return (
              <button
                key={subgroup.id}
                ref={(element) => {
                  optionRefs.current[index + 1] = element;
                }}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`subgroup-select__option${isSelected ? " subgroup-select__option--selected" : ""}`}
                onClick={() => selectOption(String(subgroup.id))}
                onKeyDown={(event) => handleOptionKeyDown(event, index + 1)}
              >
                <span className="subgroup-select__check">
                  {isSelected && <Check size={15} />}
                </span>
                <span>{subgroupLabel(subgroup)}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SubgroupSelect;
