import { Link } from 'react-router';
import { NAVIGATION } from '../layout/navigation';
import { RoleGate } from '../roles/RoleGate';

export function HomePage() {
  const views = NAVIGATION.filter((item) => item.resource !== null);
  return (
    <article className="page">
      <h1 className="page__title">Inicio</h1>
      <p>
        Consulta de los datos cargados y de los resultados ya calculados por el motor. La interfaz
        no recalcula nada: muestra lo que entrega la API.
      </p>
      <h2 className="page__subtitle">Vistas</h2>
      <ul className="link-list">
        {views.map((item) =>
          item.resource ? (
            <RoleGate key={item.to} resource={item.resource}>
              <li>
                <Link to={item.to}>{item.label}</Link>
              </li>
            </RoleGate>
          ) : null,
        )}
      </ul>
      <p className="page__note">
        El dashboard priorizado y la vista de riesgos no están disponibles en V1.
      </p>
    </article>
  );
}
