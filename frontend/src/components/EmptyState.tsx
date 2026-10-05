interface EmptyStateProps {
  title: string;
  message?: string;
}

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <section className="state state--empty" aria-label={title}>
      <h2 className="state__title">{title}</h2>
      {message ? <p className="state__message">{message}</p> : null}
    </section>
  );
}
