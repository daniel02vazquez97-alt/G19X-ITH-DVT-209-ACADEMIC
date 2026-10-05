import { Link } from 'react-router';
import { PATHS } from '../routes/paths';

export function NotFoundPage() {
  return (
    <article className="page">
      <h1 className="page__title">Página no encontrada</h1>
      <p>La dirección no corresponde a ninguna vista.</p>
      <Link to={PATHS.home}>Volver al inicio</Link>
    </article>
  );
}
