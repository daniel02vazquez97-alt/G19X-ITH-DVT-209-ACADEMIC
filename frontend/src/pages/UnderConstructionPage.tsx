interface UnderConstructionPageProps {
  title: string;
  /** Unit of Fase 7 that delivers the view (DT-070 point 24). */
  unit: 'F7d';
}

export function UnderConstructionPage({ title, unit }: UnderConstructionPageProps) {
  return (
    <article className="page">
      <h1 className="page__title">{title}</h1>
      <p className="page__note">
        En construcción: esta vista llega con la unidad {unit} de la Fase 7.
      </p>
    </article>
  );
}
