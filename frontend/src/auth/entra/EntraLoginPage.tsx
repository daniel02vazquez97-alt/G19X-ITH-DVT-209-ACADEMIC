import { useState } from 'react';
import { useAuth } from '../context';
import { entraErrorMessage } from './EntraAuthProvider';

/** Sign-in with Microsoft Entra ID (U11, DT-099): a redirect, never a password typed into this page. */
export function EntraLoginPage() {
  const { login, sessionNotice, checking } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setPending(true);
    setError(null);
    try {
      await login('');
    } catch (cause) {
      setError(entraErrorMessage(cause));
      setPending(false);
    }
  }

  return (
    <main className="login" id="contenido">
      <div className="login__panel">
        <h1 className="login__title">Motor de Abastecimiento</h1>
        <p className="login__subtitle">
          Interfaz V1 de solo lectura · entorno dev (Microsoft Entra ID)
        </p>
        {sessionNotice ? (
          <p className="login__notice" role="status">
            {sessionNotice}
          </p>
        ) : null}
        {checking ? (
          <p className="field__help" role="status">
            Comprobando la sesión…
          </p>
        ) : (
          <>
            <p className="field__help">
              Inicia sesión con tu cuenta de la organización. Los permisos dependen de los roles de
              aplicación que tengas asignados; la API los comprueba en cada petición.
            </p>
            {error ? (
              <p className="field__error" role="alert">
                {error}
              </p>
            ) : null}
            <button
              type="button"
              className="button button--primary"
              disabled={pending}
              onClick={handleLogin}
            >
              {pending ? 'Redirigiendo…' : 'Iniciar sesión con Microsoft'}
            </button>
          </>
        )}
      </div>
    </main>
  );
}
