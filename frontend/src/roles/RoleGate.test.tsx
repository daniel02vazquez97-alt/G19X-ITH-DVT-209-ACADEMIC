import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { installFetch, withMe } from '../test/api';
import { loginAs, renderApp } from '../test/renderApp';
import { ROLES, type Role } from './access';
import { RoleGate } from './RoleGate';
import { routes } from '../routes/routes';

function GateProbe() {
  return (
    <>
      <RoleGate resource="history" fallback={<p>sin historial</p>}>
        <p>historial visible</p>
      </RoleGate>
      <RoleGate resource="runs">
        <p>ejecución visible</p>
      </RoleGate>
    </>
  );
}

const EXPECTED: Record<Role, { history: boolean; runs: boolean }> = {
  VIEWER: { history: false, runs: false },
  ANALYST: { history: true, runs: false },
  PLANNER: { history: true, runs: true },
  ADMIN: { history: true, runs: true },
};

describe('RoleGate', () => {
  it.each(ROLES)('%s', async (role) => {
    routes[0]?.children?.push({ path: 'gate', element: <GateProbe /> });
    try {
      installFetch(withMe());
      const { user } = renderApp('/gate');
      await loginAs(user, role);
      expect(screen.queryByText('historial visible') !== null).toBe(EXPECTED[role].history);
      expect(screen.queryByText('sin historial') !== null).toBe(!EXPECTED[role].history);
      expect(screen.queryByText('ejecución visible') !== null).toBe(EXPECTED[role].runs);
    } finally {
      routes[0]?.children?.pop();
    }
  });
});
