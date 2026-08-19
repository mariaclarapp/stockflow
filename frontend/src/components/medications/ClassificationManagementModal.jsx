import { LoaderCircle, Pencil, Plus, Save, Tags, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

const EMPTY_FORM = {
  nome: "",
  descricao: "",
  cor: "#0B8178",
  ativo: true,
};

function ClassificationManagementModal({
  classifications,
  isSaving,
  error,
  onClose,
  onDelete,
  onSave,
}) {
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    function handleEscape(event) {
      if (event.key !== "Escape" || isSaving) return;
      if (deleteTarget) {
        setDeleteTarget(null);
      } else {
        onClose();
      }
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [deleteTarget, isSaving, onClose]);

  function startCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  function startEdit(classification) {
    setEditing(classification);
    setForm({
      nome: classification.nome,
      descricao: classification.descricao || "",
      cor: classification.cor || "#0B8178",
      ativo: classification.ativo,
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const saved = await onSave(editing, form);
    if (saved) startEdit(saved);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const deleted = await onDelete(deleteTarget);
    if (deleted) {
      setDeleteTarget(null);
      startCreate();
    } else {
      setDeleteTarget(null);
    }
  }

  const isCanonical = editing?.nome?.toUpperCase() === "MANIPULADO";

  return (
    <div className="classification-modal-overlay">
      <section
        className="classification-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="classification-modal-title"
      >
        <header className="classification-modal__header">
          <div>
            <span className="eyebrow">Organização administrativa</span>
            <h2 id="classification-modal-title">Gerenciar classificações</h2>
          </div>
          <button
            type="button"
            className="classification-icon-button"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Fechar gerenciamento de classificações"
            title="Fechar"
          >
            <X size={18} />
          </button>
        </header>

        <div className="classification-modal__body">
          <div className="classification-catalog">
            <div className="classification-catalog__heading">
              <strong>Classificações cadastradas</strong>
              <button type="button" onClick={startCreate} disabled={isSaving}>
                <Plus size={15} />
                Nova
              </button>
            </div>
            <div className="classification-catalog__list">
              {classifications.map((classification) => (
                <button
                  type="button"
                  className={`classification-catalog__item${editing?.id === classification.id ? " classification-catalog__item--active" : ""}`}
                  key={classification.id}
                  onClick={() => startEdit(classification)}
                  disabled={isSaving}
                >
                  <span
                    className="classification-color-swatch"
                    style={{ backgroundColor: classification.cor || "#D7E2DF" }}
                    aria-hidden="true"
                  />
                  <span>
                    <strong>{classification.nome}</strong>
                    <small>{classification.ativo ? "Ativa" : "Inativa"}</small>
                  </span>
                  <Pencil size={15} aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>

          <form className="classification-form" onSubmit={handleSubmit}>
            <div className="classification-form__title">
              <Tags size={18} aria-hidden="true" />
              <strong>{editing ? "Editar classificação" : "Nova classificação"}</strong>
            </div>

            <label>
              Nome
              <input
                type="text"
                value={form.nome}
                maxLength={120}
                disabled={isSaving || isCanonical}
                onChange={(event) => setForm({ ...form, nome: event.target.value })}
                required
              />
            </label>

            <label>
              Descrição
              <textarea
                value={form.descricao}
                rows={4}
                disabled={isSaving}
                onChange={(event) => setForm({ ...form, descricao: event.target.value })}
              />
            </label>

            <label>
              Cor
              <span className="classification-color-control">
                <input
                  type="color"
                  value={form.cor || "#0B8178"}
                  disabled={isSaving}
                  onChange={(event) => setForm({ ...form, cor: event.target.value })}
                />
                <span>{form.cor || "Sem cor"}</span>
              </span>
            </label>

            <label className="classification-active-control">
              <input
                type="checkbox"
                checked={form.ativo}
                disabled={isSaving || isCanonical}
                onChange={(event) => setForm({ ...form, ativo: event.target.checked })}
              />
              <span>Classificação ativa</span>
            </label>

            {isCanonical && (
              <p className="classification-form__note">
                MANIPULADO mantém nome e estado ativo protegidos pela regra de disponibilidade.
              </p>
            )}
            {error && <p className="classification-form__error" role="alert">{error}</p>}

            <div className="classification-form__actions">
              {editing && !isCanonical && (
                <button
                  type="button"
                  className="classification-delete-button"
                  onClick={() => setDeleteTarget(editing)}
                  disabled={isSaving}
                >
                  <Trash2 size={16} />
                  Excluir
                </button>
              )}
              <button
                type="submit"
                className="primary-button classification-form__submit"
                disabled={isSaving || !form.nome.trim()}
              >
                {isSaving ? (
                  <><LoaderCircle className="button-spinner" size={17} /> Salvando...</>
                ) : (
                  <><Save size={17} /> Salvar classificação</>
                )}
              </button>
            </div>
          </form>
        </div>

        {deleteTarget && (
          <div className="classification-confirm-overlay">
            <section
              className="classification-confirm"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="classification-confirm-title"
              aria-describedby="classification-confirm-description"
            >
              <span className="classification-confirm__icon" aria-hidden="true">
                <Trash2 size={20} />
              </span>
              <h3 id="classification-confirm-title">Excluir classificação</h3>
              <p id="classification-confirm-description">
                Deseja excluir esta classificação? Esta ação não poderá ser desfeita.
              </p>
              <strong>{deleteTarget.nome}</strong>
              <div className="classification-confirm__actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setDeleteTarget(null)}
                  disabled={isSaving}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="classification-confirm__delete"
                  onClick={confirmDelete}
                  disabled={isSaving}
                >
                  {isSaving ? (
                    <LoaderCircle className="button-spinner" size={16} />
                  ) : (
                    <Trash2 size={16} />
                  )}
                  Excluir classificação
                </button>
              </div>
            </section>
          </div>
        )}
      </section>
    </div>
  );
}

export default ClassificationManagementModal;
