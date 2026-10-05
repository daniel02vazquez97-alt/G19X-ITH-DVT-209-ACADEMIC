import { NavLink, Outlet } from 'react-router';
import { useAuth } from '../auth/context';
import { RoleGate } from '../roles/RoleGate';
import { NAVIGATION } from './navigation';

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? 'nav__link nav__link--active' : 'nav__link';
}

export function AppShell() {
  const { identity, logout } = useAuth();

  return (
    <div className="shell">
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <header className="shell__header">
        <div className="shell__brand">
          <span className="shell__name">Motor de Abastecimiento</span>
          <span className="shell__tag">V1 · solo lectura</span>
        </div>
        <div className="shell__session">
          <span className="shell__identity">
            <span className="visually-hidden">Sesión de </span>
            {identity?.subjectId}
            <span className="shell__roles"> · Roles: {identity?.roles.join(', ')}</span>
          </span>
          <button type="button" className="button" onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <nav className="shell__nav" aria-label="Navegación principal">
        <ul className="nav">
          {NAVIGATION.map((item) => {
            const link = (
              <li key={item.to}>
                <NavLink to={item.to} end={item.resource === null} className={navClass}>
                  {item.label}
                </NavLink>
              </li>
            );
            return item.resource === null ? (
              link
            ) : (
              <RoleGate key={item.to} resource={item.resource}>
                {link}
              </RoleGate>
            );
          })}
        </ul>
      </nav>
      <main className="shell__main" id="contenido" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
