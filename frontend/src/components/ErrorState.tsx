import { EmptyState } from './EmptyState';
import { presentError } from './errorPresentation';

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const presentation = presentError(error);
  if (presentation.kind === 'empty') {
    return <EmptyState title={presentation.title} message={presentation.message} />;
  }
  return (
    <section className="state state--error" role="alert">
      <h2 className="state__title">
        <span className="state__marker">Error:</span> {presentation.title}
      </h2>
      <p className="state__message">{presentation.message}</p>
      {presentation.correlationId ? (
        <p className="state__correlation">
          Identificador de correlación: <code>{presentation.correlationId}</code>
        </p>
      ) : null}
      {presentation.retryable && onRetry ? (
        <button type="button" className="button" onClick={onRetry}>
          Reintentar
        </button>
      ) : null}
    </section>
  );
}
