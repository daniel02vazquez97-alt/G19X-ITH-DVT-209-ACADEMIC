import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { AppProviders, createQueryClient } from '../AppProviders';
import type { Role } from '../roles/access';
import { routes } from '../routes/routes';
import { TEST_TOKENS } from './api';

export function renderApp(path = '/') {
  const queryClient = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const user = userEvent.setup();
  const view = render(
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { ...view, router, user, queryClient };
}

export async function loginAs(user: ReturnType<typeof userEvent.setup>, role: Role) {
  await user.type(screen.getByLabelText('Token de desarrollo'), TEST_TOKENS[role]);
  await user.click(screen.getByRole('button', { name: 'Entrar' }));
  await screen.findByRole('navigation', { name: 'Navegación principal' });
}
