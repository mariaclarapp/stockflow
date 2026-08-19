import { Check, ChevronDown, SlidersHorizontal } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";

function FilterSelect({
  id,
  label,
  value,
  options,
  onChange,
  placeholder,
  isLoading = false,
  loadingLabel = "Carregando...",
  icon: Icon = SlidersHorizontal,
  className = "",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const optionRefs = useRef([]);
  const selectedOption = options.find(
    (option) => String(option.value) === String(value),
  );
  const labelId = `${id}-label`;
  const optionsId = `${id}-options`;

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
    const selectedIndex = selectedOption
      ? options.findIndex((option) => option.value === selectedOption.value) + 1
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
      optionRefs.current[Math.min(index + 1, options.length)]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      optionRefs.current[Math.max(index - 1, 0)]?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      optionRefs.current[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      optionRefs.current[options.length]?.focus();
    }
  }

  return (
    <div
      className={`filter-select${className ? ` ${className}` : ""}`}
      ref={rootRef}
    >
      <span id={labelId}>{label}</span>
      <button
        ref={triggerRef}
        type="button"
        className={`filter-select__trigger${isOpen ? " filter-select__trigger--open" : ""}`}
        aria-labelledby={labelId}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={optionsId}
        disabled={isLoading}
        onClick={() => (isOpen ? setIsOpen(false) : openMenu())}
      >
        <Icon size={17} aria-hidden="true" />
        <span>
          {isLoading
            ? loadingLabel
            : selectedOption?.label || placeholder}
        </span>
        <ChevronDown
          className="filter-select__chevron"
          size={17}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          className="filter-select__options"
          id={optionsId}
          role="listbox"
          aria-labelledby={labelId}
        >
          <button
            ref={(element) => {
              optionRefs.current[0] = element;
            }}
            type="button"
            role="option"
            aria-selected={!value}
            className={`filter-select__option${!value ? " filter-select__option--selected" : ""}`}
            onClick={() => selectOption("")}
            onKeyDown={(event) => handleOptionKeyDown(event, 0)}
          >
            <span className="filter-select__check">
              {!value && <Check size={15} />}
            </span>
            <span>{placeholder}</span>
          </button>

          {options.map((option, index) => {
            const isSelected = String(option.value) === String(value);
            const showGroup = option.group
              && option.group !== options[index - 1]?.group;
            return (
              <Fragment key={option.value}>
                {showGroup && (
                  <span className="filter-select__group" aria-hidden="true">
                    {option.group}
                  </span>
                )}
                <button
                  ref={(element) => {
                    optionRefs.current[index + 1] = element;
                  }}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  className={`filter-select__option${isSelected ? " filter-select__option--selected" : ""}`}
                  onClick={() => selectOption(String(option.value))}
                  onKeyDown={(event) => handleOptionKeyDown(event, index + 1)}
                >
                  <span className="filter-select__check">
                    {isSelected && <Check size={15} />}
                  </span>
                  <span>{option.label}</span>
                </button>
              </Fragment>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default FilterSelect;
