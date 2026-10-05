import { useId, type FormEvent } from 'react';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterField {
  /** Query-string key, identical to the API parameter. */
  key: string;
  label: string;
  /** `text`: free text; `id`: an explicit identifier (no catalogue, DT-070 point 11); `select`. */
  kind: 'text' | 'id' | 'select';
  options?: readonly FilterOption[];
  help?: string;
}

interface FilterFormProps {
  fields: readonly FilterField[];
  search: URLSearchParams;
  onApply: (values: Record<string, string | null>) => void;
}

/** Filters live in the URL; the form only edits them. Applying a change goes back to page 1. */
export function FilterForm({ fields, search, onApply }: FilterFormProps) {
  const formId = useId();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const values: Record<string, string | null> = {};
    for (const field of fields) {
      const value = data.get(field.key);
      values[field.key] = typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
    }
    onApply(values);
  }

  function handleClear() {
    onApply(Object.fromEntries(fields.map((field) => [field.key, null])));
  }

  return (
    <form
      key={search.toString()}
      className="filters"
      aria-label="Filtros"
      onSubmit={handleSubmit}
      noValidate
    >
      {fields.map((field) => {
        const inputId = `${formId}-${field.key}`;
        const current = search.get(field.key) ?? '';
        return (
          <div className="filters__field" key={field.key}>
            <label htmlFor={inputId} className="field__label">
              {field.label}
            </label>
            {field.kind === 'select' ? (
              <select id={inputId} name={field.key} className="field__input" defaultValue={current}>
                {(field.options ?? []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={inputId}
                name={field.key}
                className="field__input"
                type="text"
                inputMode={field.kind === 'id' ? 'numeric' : undefined}
                autoComplete="off"
                defaultValue={current}
              />
            )}
            {field.help ? <span className="field__help">{field.help}</span> : null}
          </div>
        );
      })}
      <div className="filters__actions">
        <button type="submit" className="button button--primary">
          Aplicar
        </button>
        <button type="button" className="button" onClick={handleClear}>
          Limpiar
        </button>
      </div>
    </form>
  );
}
