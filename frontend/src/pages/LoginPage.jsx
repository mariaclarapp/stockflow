import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Brand, PharmacyIllustration } from "../components/Brand";

function LoginPage() {
  const { user, isLoading, login, sessionError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoading && user) {
    return <Navigate to="/admin" replace />;
  }

  function updateField(event) {
    setCredentials((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(credentials);
      navigate(location.state?.from?.pathname || "/admin", { replace: true });
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 400) {
        setError("Não foi possível entrar com as credenciais informadas.");
      } else {
        setError("Não foi possível acessar o sistema. Tente novamente.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-visual" aria-label="StockFlow">
        <Brand />
        <PharmacyIllustration />
      </section>

      <section className="login-card" aria-labelledby="login-title">
        <Brand compact />
        <div className="login-card__heading">
          <h1 id="login-title">Acesse sua conta</h1>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="username">Usuário</label>
          <input
            id="username"
            name="username"
            type="text"
            value={credentials.username}
            onChange={updateField}
            placeholder="Digite seu usuário"
            autoComplete="username"
            required
            disabled={isSubmitting}
          />

          <label htmlFor="password">Senha</label>
          <input
            id="password"
            name="password"
            type="password"
            value={credentials.password}
            onChange={updateField}
            placeholder="Digite sua senha"
            autoComplete="current-password"
            required
            disabled={isSubmitting}
          />

          {(error || sessionError) && (
            <p className="form-error" role="alert">
              {error || sessionError}
            </p>
          )}

          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <footer className="login-card__footer">
          <strong>Acesso administrativo</strong>
          <span>Use as credenciais fornecidas pelo sistema.</span>
        </footer>
      </section>
    </main>
  );
}

export default LoginPage;
