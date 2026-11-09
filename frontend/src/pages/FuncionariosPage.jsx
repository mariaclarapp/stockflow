import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Power,
  ShieldCheck,
  Trash2,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { createStaffUser, deleteStaffUser, getStaffUsers, updateStaffStatus } from "../api/users";

const EMPTY_FORM = {
  name: "",
  username: "",
  password: "",
  passwordConfirmation: "",
};

function errorMessage(error) {
  if (error instanceof ApiError) return error.message;
  return "Não foi possível concluir a operação.";
}

function FuncionariosPage() {
  const [employees, setEmployees] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [success, setSuccess] = useState("");
  const [listSuccess, setListSuccess] = useState("");
  const [isUpdatingId, setIsUpdatingId] = useState(null);

  const passwordRules = [
    { label: "Pelo menos 8 caracteres", valid: form.password.length >= 8 },
    { label: "Uma letra maiúscula", valid: /[A-Z]/.test(form.password) },
    { label: "Uma letra minúscula", valid: /[a-z]/.test(form.password) },
    { label: "Um número", valid: /\d/.test(form.password) },
    { label: "Um caractere especial", valid: /[^A-Za-z0-9]/.test(form.password) },
  ];
  const passwordScore = passwordRules.filter((rule) => rule.valid).length;
  const passwordIsValid = passwordScore === passwordRules.length;

  useEffect(() => {
    let isCurrent = true;
    getStaffUsers()
      .then((data) => {
        if (isCurrent) setEmployees(data);
      })
      .catch((requestError) => {
        if (isCurrent) setListError(errorMessage(requestError));
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setError("");
    setSuccess("");
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (!passwordIsValid) {
      setError("A senha ainda não atende a todos os requisitos.");
      return;
    }
    if (form.password !== form.passwordConfirmation) {
      setError("As senhas informadas não coincidem.");
      return;
    }
    setIsSaving(true);
    try {
      const employee = await createStaffUser(form);
      setEmployees((current) =>
        [...current, employee].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")),
      );
      setForm(EMPTY_FORM);
      setShowPassword(false);
      setShowPasswordConfirmation(false);
      setSuccess(`Acesso de ${employee.nome} criado com sucesso.`);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  async function toggleStatus(employee) {
    setListError("");
    setListSuccess("");
    setError("");
    setSuccess("");
    setIsUpdatingId(employee.id);
    try {
      const updated = await updateStaffStatus(employee.id, !employee.is_active);
      setEmployees((current) => current.map((item) => item.id === updated.id ? updated : item));
      setListSuccess(`Acesso de ${updated.nome} ${updated.is_active ? "ativado" : "desativado"}.`);
    } catch (requestError) {
      setListError(errorMessage(requestError));
    } finally {
      setIsUpdatingId(null);
    }
  }

  async function removeEmployee(employee) {
    if (!window.confirm(`Excluir o acesso de ${employee.nome}?`)) return;
    setListError("");
    setListSuccess("");
    setError("");
    setSuccess("");
    setIsUpdatingId(employee.id);
    try {
      await deleteStaffUser(employee.id);
      setEmployees((current) => current.filter((item) => item.id !== employee.id));
      setListSuccess(`Acesso de ${employee.nome} excluído.`);
    } catch (requestError) {
      setListError(errorMessage(requestError));
    } finally {
      setIsUpdatingId(null);
    }
  }

  return (
    <main className="staff-page">
      <header className="page-heading staff-page__heading">
        <div>
          <span className="eyebrow">Acesso administrativo</span>
          <h1>Funcionários</h1>
          <p>Crie contas para as pessoas que irão operar o StockFlow.</p>
        </div>
        <span className="staff-page__badge"><ShieldCheck size={16} />Somente superusuário</span>
      </header>

      <div className="staff-layout">
        <section className="staff-card" aria-labelledby="staff-create-title">
          <div className="staff-card__heading">
            <span><UserPlus size={20} /></span>
            <div><h2 id="staff-create-title">Cadastrar funcionário</h2><p>O acesso será liberado imediatamente.</p></div>
          </div>
          <form className="staff-form" onSubmit={submit}>
            <label>Nome do funcionário<input name="name" value={form.name} onChange={updateField} maxLength={150} autoComplete="name" placeholder="Ex.: Maria da Silva" required disabled={isSaving} /></label>
            <label>Usuário de acesso<input name="username" value={form.username} onChange={updateField} maxLength={150} autoComplete="username" placeholder="Ex.: maria.silva" required disabled={isSaving} /></label>
            <div className="staff-form__passwords">
              <label>Senha<span className="staff-password-input"><input type={showPassword ? "text" : "password"} name="password" value={form.password} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /><button type="button" className="staff-password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"} disabled={isSaving}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
              <label>Confirmar senha<span className="staff-password-input"><input type={showPasswordConfirmation ? "text" : "password"} name="passwordConfirmation" value={form.passwordConfirmation} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /><button type="button" className="staff-password-toggle" onClick={() => setShowPasswordConfirmation((visible) => !visible)} aria-label={showPasswordConfirmation ? "Ocultar confirmação de senha" : "Mostrar confirmação de senha"} disabled={isSaving}>{showPasswordConfirmation ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
            </div>
            <div className="staff-password-strength" aria-live="polite">
              <div className="staff-password-strength__heading"><span><KeyRound size={15} />Requisitos da senha</span><strong>{passwordScore}/5</strong></div>
              <div className="staff-password-strength__bar" aria-hidden="true"><span style={{ width: `${passwordScore * 20}%` }} /></div>
              <ul>{passwordRules.map((rule) => <li className={rule.valid ? "is-valid" : ""} key={rule.label}>{rule.valid ? <CheckCircle2 size={15} /> : <Circle size={15} />}<span>{rule.label}</span></li>)}</ul>
              {form.passwordConfirmation && form.password !== form.passwordConfirmation && <p className="staff-password-mismatch">As senhas não coincidem.</p>}
            </div>
            <p className="staff-form__help"><KeyRound size={15} />Use uma senha diferente do nome e do usuário, evitando sequências e senhas comuns.</p>
            {error && <div className="staff-feedback staff-feedback--error" role="alert"><AlertCircle size={17} /><span>{error}</span></div>}
            {success && <div className="staff-feedback staff-feedback--success" role="status"><CheckCircle2 size={17} /><span>{success}</span></div>}
            <button className="primary-button staff-form__submit" type="submit" disabled={isSaving || !passwordIsValid || form.password !== form.passwordConfirmation}>
              {isSaving ? <LoaderCircle className="button-spinner" size={17} /> : <UserPlus size={17} />}
              Criar acesso
            </button>
          </form>
        </section>

        <section className="staff-card" aria-labelledby="staff-list-title">
          <div className="staff-card__heading">
            <span><UsersRound size={20} /></span>
            <div><h2 id="staff-list-title">Acessos cadastrados</h2><p>Contas de funcionários, sem privilégios de superusuário.</p></div>
          </div>
          {listError && <div className="staff-feedback staff-feedback--error staff-list__feedback" role="alert"><AlertCircle size={17} /><span>{listError}</span></div>}
          {listSuccess && <div className="staff-feedback staff-feedback--success staff-list__feedback" role="status"><CheckCircle2 size={17} /><span>{listSuccess}</span></div>}
          {isLoading ? <div className="staff-state"><LoaderCircle className="button-spinner" size={22} />Carregando acessos...</div> : employees.length ? (
            <ul className="staff-list">
              {employees.map((employee) => <li key={employee.id}><span className="staff-list__avatar">{employee.nome.slice(0, 1).toUpperCase()}</span><span><strong>{employee.nome}</strong><small>@{employee.username}</small></span><span className="staff-list__actions"><b className={employee.is_active ? "staff-status staff-status--active" : "staff-status"}>{employee.is_active ? "Ativo" : "Inativo"}</b><button type="button" className="staff-list__action" onClick={() => toggleStatus(employee)} disabled={isUpdatingId === employee.id} aria-label={employee.is_active ? `Desativar ${employee.nome}` : `Ativar ${employee.nome}`} title={employee.is_active ? "Desativar acesso" : "Ativar acesso"}>{isUpdatingId === employee.id ? <LoaderCircle className="button-spinner" size={15} /> : <Power size={15} />}</button>{!employee.is_active && <button type="button" className="staff-list__action staff-list__action--danger" onClick={() => removeEmployee(employee)} disabled={isUpdatingId === employee.id} aria-label={`Excluir ${employee.nome}`} title="Excluir acesso"><Trash2 size={15} /></button>}</span></li>)}
            </ul>
          ) : <div className="staff-state"><UsersRound size={22} />Nenhum funcionário cadastrado.</div>}
        </section>
      </div>
    </main>
  );
}

export default FuncionariosPage;
