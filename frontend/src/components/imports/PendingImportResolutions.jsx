import { AlertCircle, Link2, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { resolveImportPending } from "../../api/inventory";

function formatQuantity(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(numeric);
}

function PendingImportResolutions({ importId, pendencias, onResolved, compact = false }) {
  const [codes, setCodes] = useState({});
  const [resolvingId, setResolvingId] = useState(null);
  const [errors, setErrors] = useState({});

  if (!pendencias?.length) return null;

  async function handleResolve(pendencia) {
    const code = (codes[pendencia.id] || "").trim();
    if (!code) {
      setErrors((current) => ({ ...current, [pendencia.id]: "Informe o código G-MUS correto." }));
      return;
    }
    setResolvingId(pendencia.id);
    setErrors((current) => ({ ...current, [pendencia.id]: "" }));
    try {
      const response = await resolveImportPending(importId, pendencia.id, code);
      onResolved?.(response);
    } catch (requestError) {
      setErrors((current) => ({
        ...current,
        [pendencia.id]: requestError.message || "Não foi possível resolver a pendência.",
      }));
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <section className={`import-pending${compact ? " import-pending--compact" : ""}`}>
      <header>
        <AlertCircle size={18} aria-hidden="true" />
        <div>
          <strong>{pendencias.length} medicamento(s) aguardando identificação</strong>
          <small>Informe o código G-MUS correto para incorporar a quantidade ao estoque.</small>
        </div>
      </header>
      <div className="import-pending__list">
        {pendencias.map((pendencia) => (
          <article key={pendencia.id}>
            <div className="import-pending__description">
              <strong>{pendencia.descricao}</strong>
              <small>
                Linha {pendencia.linha} · {pendencia.unidade || "Unidade não informada"} · Quantidade {formatQuantity(pendencia.quantidade)}
              </small>
            </div>
            <div className="import-pending__form">
              <label htmlFor={`pending-code-${pendencia.id}`}>Código G-MUS correto</label>
              <div>
                <input
                  id={`pending-code-${pendencia.id}`}
                  value={codes[pendencia.id] || ""}
                  placeholder="Ex.: 184.1"
                  inputMode="decimal"
                  disabled={resolvingId === pendencia.id}
                  onChange={(event) => setCodes((current) => ({
                    ...current,
                    [pendencia.id]: event.target.value,
                  }))}
                />
                <button
                  className="secondary-button"
                  type="button"
                  disabled={resolvingId !== null}
                  onClick={() => handleResolve(pendencia)}
                >
                  {resolvingId === pendencia.id
                    ? <><LoaderCircle className="button-spinner" size={15} />Associando...</>
                    : <><Link2 size={15} />Associar</>}
                </button>
              </div>
              {errors[pendencia.id] && <p role="alert">{errors[pendencia.id]}</p>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default PendingImportResolutions;
