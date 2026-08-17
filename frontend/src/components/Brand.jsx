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
      <div className="pharmacy-illustration__halo" />
      <Plus className="pharmacy-illustration__cross" size={58} strokeWidth={4} />
      <div className="pharmacy-illustration__cabinet">
        <div className="medicine-row">
          <span className="medicine-box medicine-box--mint" />
          <span className="medicine-bottle medicine-bottle--amber" />
          <span className="medicine-box medicine-box--cream medicine-box--wide" />
          <span className="medicine-bottle medicine-bottle--pale" />
        </div>
        <span className="cabinet-shelf" />
        <div className="medicine-row medicine-row--middle">
          <span className="medicine-box medicine-box--soft" />
          <span className="medicine-box medicine-box--cream medicine-box--wide" />
          <span className="medicine-bottle medicine-bottle--pale" />
          <span className="medicine-bottle medicine-bottle--amber" />
        </div>
        <span className="cabinet-shelf" />
        <div className="medicine-row medicine-row--bottom">
          <span className="medicine-box medicine-box--cream" />
          <span className="medicine-bottle medicine-bottle--pale" />
          <span className="medicine-box medicine-box--soft" />
        </div>
        <span className="cabinet-shelf" />
        <span className="medicine-capsule" />
      </div>
    </div>
  );
}
