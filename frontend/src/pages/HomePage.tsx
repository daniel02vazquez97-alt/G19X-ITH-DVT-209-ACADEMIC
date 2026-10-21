import { Link } from 'react-router';
import { NAVIGATION } from '../layout/navigation';
import { RoleGate } from '../roles/RoleGate';

// How a recommendation is produced, in the order the system runs it (docs/00-guia-maestra.md). Text only: the
// home page shows no figures.
const STEPS = [
  {
    title: 'Datos',
    text: 'Histórico de consumo, inventario, plazos de entrega y proveedores cargados en PostgreSQL.',
  },
  {
    title: 'Pronóstico',
    text: 'Demanda semanal de cada producto con un modelo base reproducible.',
  },
  {
    title: 'Recomendación',
    text: 'Reglas deterministas deciden qué comprar, cuánto y cuándo; cada cifra se puede reconstruir.',
  },
  {
    title: 'Explicación',
    text: 'La IA describe el resultado ya calculado y se comprueba cifra a cifra; no decide nada.',
  },
];

export function HomePage() {
  const views = NAVIGATION.filter((item) => item.resource !== null);
  return (
    <article className="page home">
      <header className="hero">
        <p className="hero__eyebrow">Inicio</p>
        <h1 className="hero__title">Apoyo a la decisión de compras</h1>
        <p className="hero__lead">
          Consulta de los datos cargados y de los resultados ya calculados por el motor. La interfaz
          no recalcula nada: muestra lo que entrega la API.
        </p>
      </header>

      <section className="section" aria-labelledby="vistas">
        <h2 id="vistas" className="section__title">
          Vistas
        </h2>
        <ul className="card-grid">
          {views.map((item) =>
            item.resource ? (
              <RoleGate key={item.to} resource={item.resource}>
                <li>
                  <Link to={item.to} className="nav-card">
                    <span className="nav-card__title">{item.label}</span>
                    <span className="nav-card__text">{item.description}</span>
                    <span className="nav-card__arrow" aria-hidden="true">
                      →
                    </span>
                  </Link>
                </li>
              </RoleGate>
            ) : null,
          )}
        </ul>
      </section>

      <section className="section" aria-labelledby="como-funciona">
        <h2 id="como-funciona" className="section__title">
          Cómo se calcula una recomendación
        </h2>
        <ol className="steps">
          {STEPS.map((step) => (
            <li key={step.title} className="steps__item">
              <span className="steps__title">{step.title}</span>
              <span className="steps__text">{step.text}</span>
            </li>
          ))}
        </ol>
      </section>

      <p className="page__note">
        El dashboard priorizado y la vista de riesgos no están disponibles en V1.
      </p>
    </article>
  );
}
