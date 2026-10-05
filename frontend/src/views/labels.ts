// Small presentation texts shared by the views. Codes from the API are shown as they are when the
// interface has no agreed wording for them.
import { formatCalendarDate } from '../format/dates';

export function yesNo(value: boolean): string {
  return value ? 'Sí' : 'No';
}

export function activeLabel(isActive: boolean): string {
  return isActive ? 'Activo' : 'Inactivo';
}

export function validityLabel(validFrom: string, validTo: string | null): string {
  return `${formatCalendarDate(validFrom)} – ${validTo ? formatCalendarDate(validTo) : 'sin fecha de fin'}`;
}
