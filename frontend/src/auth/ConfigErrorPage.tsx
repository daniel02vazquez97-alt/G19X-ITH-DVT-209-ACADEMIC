/** A `dev` build with an incomplete Entra ID configuration fails closed (U11, DT-099). */
export function ConfigErrorPage({ problems }: { problems: string[] }) {
  return (
    <main className="login" id="contenido">
      <div className="login__panel">
        <h1 className="login__title">Configuración incompleta</h1>
        <p className="login__subtitle">
          Esta compilación es para Microsoft Entra ID (VITE_APP_ENV=dev) y le faltan datos.
        </p>
        <ul role="alert">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      </div>
    </main>
  );
}
