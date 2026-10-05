// Notices of `provenance.notices` (DT-066, DT-070 point 16). Only the notices the API sends are
// shown; the interface never adds its own.

const NOTICE_TEXTS: Record<string, string> = {
  SYNTHETIC_DATA: 'Datos sintéticos: las cifras no proceden de una operación real.',
  V1_PROVISIONAL_POLICY:
    'Política provisional V1: el resultado no es una recomendación de negocio definitiva.',
};

export function noticeText(code: string): string {
  return NOTICE_TEXTS[code] ?? `Aviso ${code}.`;
}

interface NoticeBannerProps {
  notices: readonly string[];
}

export function NoticeBanner({ notices }: NoticeBannerProps) {
  if (notices.length === 0) {
    return null;
  }
  return (
    <aside className="notice" aria-label="Avisos">
      <ul className="notice__list">
        {notices.map((code) => (
          <li key={code} className="notice__item" data-notice={code}>
            <strong>Aviso:</strong> {noticeText(code)}
          </li>
        ))}
      </ul>
    </aside>
  );
}
