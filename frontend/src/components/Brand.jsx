import { Plus } from "lucide-react";

export function Brand({ compact = false }) {
  return (
    <div className={`brand${compact ? " brand--compact" : ""}`}>
      <span className="brand__mark" aria-hidden="true">
        <Plus size={compact ? 16 : 20} strokeWidth={3} />
      </span>
      <span>
        <strong>StockFlow</strong>
        {!compact && <small>Gestão de estoque farmacêutico</small>}
      </span>
    </div>
  );
}

export function PharmacyIllustration() {
  return (
    <div className="pharmacy-illustration" aria-hidden="true">
      <div className="pharmacy-illustration__art">
        <img src="/prateleira-farmacia.svg" alt="" />
      </div>
    </div>
  );
}
