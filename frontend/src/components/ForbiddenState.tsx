import { FORBIDDEN_TITLE } from './errorPresentation';

/** Shown in place of content the role cannot see. Visual aid only: the backend enforces roles. */
export function ForbiddenState() {
  return (
    <section className="state state--error" role="alert">
      <h2 className="state__title">{FORBIDDEN_TITLE}</h2>
      <p className="state__message">Tu rol no permite consultar este recurso.</p>
    </section>
  );
}
