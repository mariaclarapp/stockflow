import { AlertTriangle, LoaderCircle, Save, X } from "lucide-react";
import { useState } from "react";

import { formatDecimal } from "../utils/formatters";

function StockCorrectionModal({ error, isSubmitting, item, onCancel, onConfirm }) {
  const [correctedStock, setCorrectedStock] = useState(
    () => item?.estoque_esperado ?? "",
  );
  const [reason, setReason] = useState("");

  if (!item) return null;

  function submit(event) {
    event.preventDefault();
    onConfirm({ correctedStock, reason: reason.trim() });
  }

  return (
    <div className="confirmation-overlay">
      <section
        className="confirmation-dialog stock-correction-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stock-correction-title"
      >
        <span className="confirmation-dialog__icon" aria-hidden="true">
          <AlertTriangle size={22} />
        </span>
        <div className="confirmation-dialog__content">
          <div className="stock-correction-dialog__heading">
            <div>
              <h2 id="stock-correction-title">Corrigir divergência</h2>
              <p>{item.medicamento.descricao} · {item.medicamento.codigo_gmus}</p>
            </div>
            <button className="stock-correction-close" type="button" onClick={onCancel} disabled={isSubmitting} aria-label="Fechar">
              <X size={17} />
            </button>
          </div>
        </div>
        <form className="stock-correction-form" onSubmit={submit}>
          <div className="stock-correction-comparison">
            <div><small>Saldo importado</small><strong>{formatDecimal(item.estoque_observado)}</strong></div>
            <div><small>Saldo esperado</small><strong>{formatDecimal(item.estoque_esperado)}</strong></div>
            <div><small>Diferença</small><strong>{formatDecimal(item.diferenca)}</strong></div>
          </div>
          <label className="field-label">
            Saldo final correto
            <input type="number" min="0" step="0.001" value={correctedStock} onChange={(event) => setCorrectedStock(event.target.value)} required disabled={isSubmitting} />
          </label>
          <label className="field-label">
            Justificativa da correção
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} minLength={5} maxLength={1000} rows={4} placeholder="Explique por que o saldo importado precisa ser corrigido." required disabled={isSubmitting} />
          </label>
          <p className="stock-correction-help">A correção não altera o CSV nem o saldo original. Ela fica registrada na validação com usuário, data e fontes utilizadas.</p>
          {error && <p className="stock-correction-error" role="alert">{error}</p>}
          <div className="confirmation-dialog__actions">
            <button className="secondary-button" type="button" onClick={onCancel} disabled={isSubmitting}>Cancelar</button>
            <button className="primary-button" type="submit" disabled={isSubmitting || !correctedStock || reason.trim().length < 5}>
              {isSubmitting ? <LoaderCircle className="button-spinner" size={17} /> : <Save size={17} />}
              Salvar e validar
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default StockCorrectionModal;
