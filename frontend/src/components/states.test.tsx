import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/errors';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { LoadingSkeleton } from './LoadingSkeleton';
import { NoticeBanner } from './NoticeBanner';

function apiError(status: number, path = '/v1/products') {
  return new ApiError({ status, code: 'X', message: 'x', correlationId: 'corr-abc-0001', path });
}

describe('ErrorState', () => {
  it('shows a 500 with its correlation id and no technical detail', () => {
    render(<ErrorState error={apiError(500)} />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Error interno');
    expect(alert).toHaveTextContent('corr-abc-0001');
    expect(alert).not.toHaveTextContent('Traceback');
  });

  it('offers a retry on 503', async () => {
    const onRetry = vi.fn();
    render(<ErrorState error={apiError(503)} onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Servicio no disponible');
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('does not offer a retry on 403', () => {
    render(<ErrorState error={apiError(403)} onRetry={() => undefined} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Sin permiso para ver esto');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders the empty state for a 404 of a product forecast', () => {
    render(<ErrorState error={apiError(404, '/v1/products/3/forecast')} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sin datos' })).toBeInTheDocument();
  });
});

describe('loading and empty states', () => {
  it('LoadingSkeleton is a busy status with an accessible label', () => {
    render(<LoadingSkeleton lines={2} />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-busy', 'true');
    expect(status).toHaveTextContent('Cargando…');
  });

  it('EmptyState shows its title and message', () => {
    render(<EmptyState title="Sin resultados" message="No hay productos con esos filtros." />);
    expect(screen.getByRole('heading', { name: 'Sin resultados' })).toBeInTheDocument();
    expect(screen.getByText('No hay productos con esos filtros.')).toBeInTheDocument();
  });
});

describe('NoticeBanner', () => {
  it('shows the notices it receives, as text', () => {
    render(<NoticeBanner notices={['SYNTHETIC_DATA', 'V1_PROVISIONAL_POLICY']} />);
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Datos sintéticos');
    expect(items[1]).toHaveTextContent('Política provisional V1');
  });

  it('renders nothing without notices', () => {
    const { container } = render(<NoticeBanner notices={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
