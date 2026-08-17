import { FileSpreadsheet, RefreshCw, Trash2, Upload } from "lucide-react";

function formatFileSize(size) {
  if (size < 1024) return `${size} bytes`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function InventoryFilePicker({ file, disabled, onChange, onRemove }) {
  const inputId = "inventory-file";

  function handleChange(event) {
    onChange(event.target.files?.[0] || null);
    event.target.value = "";
  }

  return (
    <div className={`file-picker${file ? " file-picker--selected" : ""}`}>
      <input
        className="visually-hidden file-picker__input"
        id={inputId}
        type="file"
        accept=".csv,text/csv"
        onChange={handleChange}
        disabled={disabled}
      />

      {file ? (
        <div className="selected-file">
          <span className="selected-file__icon" aria-hidden="true">
            <FileSpreadsheet size={26} />
          </span>
          <span className="selected-file__details">
            <strong>{file.name}</strong>
            <small>{formatFileSize(file.size)}</small>
          </span>
          <div className="selected-file__actions">
            <label className="secondary-button" htmlFor={inputId}>
              <RefreshCw size={16} />
              Trocar
            </label>
            <button
              type="button"
              className="icon-button icon-button--danger"
              onClick={onRemove}
              disabled={disabled}
              aria-label="Remover arquivo"
              title="Remover arquivo"
            >
              <Trash2 size={17} />
            </button>
          </div>
        </div>
      ) : (
        <div className="file-picker__empty">
          <span className="file-picker__icon" aria-hidden="true">
            <Upload size={28} />
          </span>
          <div>
            <strong>Selecione o relatório de inventário</strong>
            <p>Arquivo CSV exportado pelo G-MUS.</p>
          </div>
          <label className="secondary-button" htmlFor={inputId}>
            Escolher arquivo
          </label>
        </div>
      )}
    </div>
  );
}

export default InventoryFilePicker;
