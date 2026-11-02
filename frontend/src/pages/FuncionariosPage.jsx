import {
  AlertCircle,
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  ShieldCheck,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { createStaffUser, getStaffUsers } from "../api/users";

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
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let isCurrent = true;
    getStaffUsers()
      .then((data) => {
        if (isCurrent) setEmployees(data);
      })
      .catch((requestError) => {
        if (isCurrent) setError(errorMessage(requestError));
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
      setSuccess(`Acesso de ${employee.nome} criado com sucesso.`);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsSaving(false);
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
              <label>Senha<input type="password" name="password" value={form.password} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /></label>
              <label>Confirmar senha<input type="password" name="passwordConfirmation" value={form.passwordConfirmation} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /></label>
            </div>
            <p className="staff-form__help"><KeyRound size={15} />Use uma senha diferente do nome e do usuário, evitando sequências e senhas comuns.</p>
            {error && <div className="staff-feedback staff-feedback--error" role="alert"><AlertCircle size={17} /><span>{error}</span></div>}
            {success && <div className="staff-feedback staff-feedback--success" role="status"><CheckCircle2 size={17} /><span>{success}</span></div>}
            <button className="primary-button staff-form__submit" type="submit" disabled={isSaving}>
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
          {isLoading ? <div className="staff-state"><LoaderCircle className="button-spinner" size={22} />Carregando acessos...</div> : employees.length ? (
            <ul className="staff-list">
              {employees.map((employee) => <li key={employee.id}><span className="staff-list__avatar">{employee.nome.slice(0, 1).toUpperCase()}</span><span><strong>{employee.nome}</strong><small>@{employee.username}</small></span><b className={employee.is_active ? "staff-status staff-status--active" : "staff-status"}>{employee.is_active ? "Ativo" : "Inativo"}</b></li>)}
            </ul>
          ) : <div className="staff-state"><UsersRound size={22} />Nenhum funcionário cadastrado.</div>}
        </section>
      </div>
    </main>
  );
}

export default FuncionariosPage;
