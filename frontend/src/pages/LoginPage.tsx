import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const destination = (location.state as { from?: string } | null)?.from ?? "/";

  if (user) return <Navigate to={destination} replace />;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      navigate(destination, { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo iniciar sesión.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-hero">
        <div className="login-hero-content">
          <span className="eyebrow">Universidad y laboratorio</span>
          <h1>Análisis visual preliminar con trazabilidad experta</h1>
          <p>
            Integra imágenes de caja Petri y microscopía, conserva la explicación automática y
            registra la decisión final del especialista.
          </p>
          <div className="scope-note">
            <strong>Alcance responsable</strong>
            <span>No identifica género o especie y no sustituye el criterio microbiológico.</span>
          </div>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="brand login-brand">
            <span className="brand-mark">BM</span>
            <div>
              <strong>BlueberryMicroID</strong>
              <small>Acceso al sistema</small>
            </div>
          </div>
          <div>
            <span className="eyebrow">Bienvenido</span>
            <h2>Iniciar sesión</h2>
            <p className="muted">Ingresa con la cuenta asignada por el administrador.</p>
          </div>

          {error && <div className="alert alert-error" role="alert">{error}</div>}

          <label className="field">
            <span>Usuario</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button className="button button-primary button-full" disabled={submitting} type="submit">
            {submitting ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </section>
    </div>
  );
}
