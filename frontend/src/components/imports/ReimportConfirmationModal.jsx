import { AlertTriangle, RefreshCw } from "lucide-react";

function ReimportConfirmationModal({ isSubmitting, onCancel, onConfirm }) {
  return (
    <div className="confirmation-overlay">
      <section
        className="confirmation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reimport-title"
        aria-describedby="reimport-description"
      >
        <span className="confirmation-dialog__icon" aria-hidden="true">
          <AlertTriangle size={22} />
        </span>
        <div className="confirmation-dialog__content">
          <h2 id="reimport-title">Confirmar reimportação</h2>
          <p id="reimport-description">
            Esta ação substituirá os dados de estoque já importados para esta
            competência e UPS. Deseja continuar?
          </p>
        </div>
        <div className="confirmation-dialog__actions">
          <button
            className="secondary-button"
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancelar
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            autoFocus
          >
            <RefreshCw size={17} aria-hidden="true" />
            Confirmar reimportação
          </button>
        </div>
      </section>
    </div>
  );
}

export default ReimportConfirmationModal;
