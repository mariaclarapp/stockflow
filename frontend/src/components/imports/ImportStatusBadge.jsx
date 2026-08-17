import { AlertTriangle, CheckCircle2 } from "lucide-react";

const statusConfig = {
  concluida: {
    label: "Concluída",
    tone: "success",
    icon: CheckCircle2,
  },
  concluida_com_alertas: {
    label: "Concluída com alertas",
    tone: "warning",
    icon: AlertTriangle,
  },
  concluida_parcial: {
    label: "Concluída parcialmente",
    tone: "partial",
    icon: AlertTriangle,
  },
};

function ImportStatusBadge({ status }) {
  const config = statusConfig[status];
  if (!config) return null;
  const Icon = config.icon;

  return (
    <span className={`status-badge status-badge--${config.tone}`}>
      <Icon size={15} />
      {config.label}
    </span>
  );
}

export default ImportStatusBadge;
