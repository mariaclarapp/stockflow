import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  X,
} from "lucide-react";
import { useState } from "react";

import { ApiError } from "../api/client";
import { changePassword } from "../api/account";

const EMPTY_FORM = {
  currentPassword: "",
  password: "",
  passwordConfirmation: "",
};

function errorMessage(error) {
  if (error instanceof ApiError) return error.message;
  return "Não foi possível alterar a senha.";
}

function PasswordChangeCard({ onClose = null }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const rules = [
    { label: "Pelo menos 8 caracteres", valid: form.password.length >= 8 },
    { label: "Uma letra maiúscula", valid: /[A-Z]/.test(form.password) },
    { label: "Uma letra minúscula", valid: /[a-z]/.test(form.password) },
    { label: "Um número", valid: /\d/.test(form.password) },
    { label: "Um caractere especial", valid: /[^A-Za-z0-9]/.test(form.password) },
  ];
  const score = rules.filter((rule) => rule.valid).length;
  const isValid = score === rules.length && form.password === form.passwordConfirmation;

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setError("");
    setSuccess("");
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (!isValid) {
      setError("A nova senha ainda não atende a todos os requisitos.");
      return;
    }
    setIsSaving(true);
    try {
      await changePassword(form);
      setForm(EMPTY_FORM);
      setShowCurrent(false);
      setShowPassword(false);
      setShowConfirmation(false);
      setSuccess("Senha alterada com sucesso.");
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className={"staff-card account-password-card" + (onClose ? " account-password-card--modal" : "")} aria-labelledby="password-title">
      <div className="staff-card__heading">
        <span><LockKeyhole size={20} /></span>
        <div><h2 id="password-title">Alterar senha de acesso</h2><p>A senha nova será protegida pelo Django.</p></div>
        {onClose && <button type="button" className="icon-button account-password-card__close" onClick={onClose} aria-label="Fechar redefinição de senha"><X size={19} /></button>}
      </div>
      <form className="staff-form" onSubmit={submit}>
        <label>Senha atual<span className="staff-password-input"><input type={showCurrent ? "text" : "password"} name="currentPassword" value={form.currentPassword} onChange={updateField} autoComplete="current-password" required disabled={isSaving} /><button type="button" className="staff-password-toggle" onClick={() => setShowCurrent((visible) => !visible)} aria-label={showCurrent ? "Ocultar senha atual" : "Mostrar senha atual"} disabled={isSaving}>{showCurrent ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
        <div className="staff-form__passwords">
          <label>Nova senha<span className="staff-password-input"><input type={showPassword ? "text" : "password"} name="password" value={form.password} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /><button type="button" className="staff-password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Ocultar nova senha" : "Mostrar nova senha"} disabled={isSaving}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
          <label>Confirmar nova senha<span className="staff-password-input"><input type={showConfirmation ? "text" : "password"} name="passwordConfirmation" value={form.passwordConfirmation} onChange={updateField} autoComplete="new-password" required disabled={isSaving} /><button type="button" className="staff-password-toggle" onClick={() => setShowConfirmation((visible) => !visible)} aria-label={showConfirmation ? "Ocultar confirmação" : "Mostrar confirmação"} disabled={isSaving}>{showConfirmation ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
        </div>
        <div className="staff-password-strength" aria-live="polite">
          <div className="staff-password-strength__heading"><span><KeyRound size={15} />Requisitos da senha</span><strong>{score}/5</strong></div>
          <div className="staff-password-strength__bar" aria-hidden="true"><span style={{ width: score * 20 + "%" }} /></div>
          <ul>{rules.map((rule) => <li className={rule.valid ? "is-valid" : ""} key={rule.label}>{rule.valid ? <CheckCircle2 size={15} /> : <Circle size={15} />}<span>{rule.label}</span></li>)}</ul>
          {form.passwordConfirmation && form.password !== form.passwordConfirmation && <p className="staff-password-mismatch">As senhas não coincidem.</p>}
        </div>
        <p className="staff-form__help"><KeyRound size={15} />Use uma senha diferente do nome e do usuário, evitando sequências e senhas comuns.</p>
        {error && <div className="staff-feedback staff-feedback--error" role="alert"><AlertCircle size={17} /><span>{error}</span></div>}
        {success && <div className="staff-feedback staff-feedback--success" role="status"><CheckCircle2 size={17} /><span>{success}</span></div>}
        <button className="primary-button staff-form__submit" type="submit" disabled={isSaving || !form.currentPassword || !isValid}>
          {isSaving ? <LoaderCircle className="button-spinner" size={17} /> : <LockKeyhole size={17} />}
          <span>{isSaving ? "Salvando..." : "Salvar nova senha"}</span>
        </button>
      </form>
    </section>
  );
}

export default PasswordChangeCard;
