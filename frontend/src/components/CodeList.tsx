/** A list of API codes (flags, reasons, parameters), shown as they are. */
export function CodeList({
  codes,
  empty = 'Ninguno',
}: {
  codes: readonly string[];
  empty?: string;
}) {
  if (codes.length === 0) {
    return <span className="muted">{empty}</span>;
  }
  return (
    <ul className="code-list">
      {codes.map((code) => (
        <li key={code}>
          <code>{code}</code>
        </li>
      ))}
    </ul>
  );
}
