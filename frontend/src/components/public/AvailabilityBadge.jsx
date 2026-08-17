import { AlertCircle, CheckCircle2, FlaskConical, HelpCircle } from "lucide-react";

const appearanceByStatus = {
  "Disponível": { tone: "available", icon: CheckCircle2 },
  "Indisponível": { tone: "unavailable", icon: AlertCircle },
  "Disponibilidade não informada": { tone: "unknown", icon: HelpCircle },
  "Disponível sob manipulação, confirmar disponibilidade": {
    tone: "compounded",
    icon: FlaskConical,
  },
};

function AvailabilityBadge({ status }) {
  const appearance = appearanceByStatus[status] || {
    tone: "unknown",
    icon: HelpCircle,
  };
  const Icon = appearance.icon;

  return (
    <span className={`availability-badge availability-badge--${appearance.tone}`}>
      <Icon size={17} aria-hidden="true" />
      <span>{status}</span>
    </span>
  );
}

export default AvailabilityBadge;
