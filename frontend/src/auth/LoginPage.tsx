import { useId, useState, type FormEvent } from 'react';
import { isApiError } from '../api/errors';
import { presentError } from '../components/errorPresentation';
import { useAuth } from './context';

function loginErrorMessage(error: unknown): string {
  if (isApiError(error) && error.status === 401) {
    return 'El token no es válido o no está registrado en la API local.';
  }
  const presentation = presentError(error);
  return presentation.correlationId
    ? `${presentation.title}. ${presentation.message} Identificador de correlación: ${presentation.correlationId}.`
    : `${presentation.title}. ${presentation.message}`;
}

export function LoginPage() {
  const { login, sessionNotice } = useAuth();
  const inputId = useId();
  const helpId = useId();
  const [credential, setCredential] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (credential.trim() === '') {
      setError('Introduce un token de desarrollo.');
      return;
    }
    setPending(true);
    setError(null);
    try {
      await login(credential);
    } catch (cause) {
      setError(loginErrorMessage(cause));
      setPending(false);
    }
  }

  return (
    <main className="login" id="contenido">
      <div className="login__panel">
        <h1 className="login__title">Motor de Abastecimiento</h1>
        <p className="login__subtitle">Interfaz V1 de solo lectura · entorno local</p>
        {sessionNotice ? (
          <p className="login__notice" role="status">
            {sessionNotice}
          </p>
        ) : null}
        <form className="login__form" onSubmit={handleSubmit} noValidate>
          <label htmlFor={inputId} className="field__label">
            Token de desarrollo
          </label>
          <input
            id={inputId}
            name="token"
            type="password"
            className="field__input"
            autoComplete="off"
            spellCheck={false}
            aria-describedby={helpId}
            aria-invalid={error !== null}
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
          />
          <p id={helpId} className="field__help">
            Pega un token <code>dev-…</code> registrado en <code>DEV_AUTH_IDENTITIES</code> de la
            API local. La sesión vive solo en memoria: al recargar la página hay que volver a
            entrar.
          </p>
          {error ? (
            <p className="field__error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="button button--primary" disabled={pending}>
            {pending ? 'Validando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </main>
  );
}
