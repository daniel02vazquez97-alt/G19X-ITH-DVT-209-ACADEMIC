import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ROLES } from '../roles/access';
import { installFetch, withMe } from '../test/api';
import { loginAs, renderApp } from '../test/renderApp';

const MENU = ['Inicio', 'Productos', 'Inventario', 'Recomendaciones', 'Predicciones'];

describe('navigation by role', () => {
  it.each(ROLES)('%s sees the V1 views and nothing deferred', async (role) => {
    installFetch(withMe());
    const { user } = renderApp('/');
    await loginAs(user, role);
    const nav = screen.getByRole('navigation', { name: 'Navegación principal' });
    const labels = within(nav)
      .getAllByRole('link')
      .map((link) => link.textContent);
    expect(labels).toEqual(MENU);
    expect(
      within(nav).queryByText(/Dashboard|Riesgos|Proveedores|Administración|Asistente/),
    ).toBeNull();
  });

  it('the home page mentions once that the dashboard and risks are not in V1', async () => {
    installFetch(withMe());
    const { user } = renderApp('/');
    await loginAs(user, 'VIEWER');
    expect(screen.getAllByText(/no están disponibles en V1/)).toHaveLength(1);
  });

  it.each([
    ['/recomendaciones/4', 'Detalle de recomendación', 'F7c'],
    ['/predicciones', 'Predicciones', 'F7d'],
  ])('%s is a stable route under construction', async (path, title, unit) => {
    installFetch(withMe());
    const { user } = renderApp(path);
    await loginAs(user, 'VIEWER');
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`unidad ${unit}`))).toBeInTheDocument();
  });

  it.each([
    ['VIEWER', false],
    ['ANALYST', false],
    ['PLANNER', true],
    ['ADMIN', true],
  ] as const)('run detail for %s: visible = %s', async (role, visible) => {
    installFetch(withMe());
    const { user } = renderApp('/ejecuciones/2');
    await loginAs(user, role);
    if (visible) {
      expect(screen.getByRole('heading', { name: 'Detalle de ejecución' })).toBeInTheDocument();
    } else {
      expect(screen.getByRole('alert')).toHaveTextContent('Sin permiso para ver esto');
    }
  });

  it('an unknown URL shows "Página no encontrada"', async () => {
    installFetch(withMe());
    const { user } = renderApp('/no-existe');
    await loginAs(user, 'VIEWER');
    expect(screen.getByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument();
  });
});
