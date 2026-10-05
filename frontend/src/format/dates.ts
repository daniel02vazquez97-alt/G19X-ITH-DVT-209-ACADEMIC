// Dates (DT-070 point 22): the API is in UTC. Calendar dates (`as_of_date`, `period_start`…) are shown
// without any time-zone conversion; timestamps (`generated_at`, `last_movement_at`…) are converted
// from UTC to the business time zone.
import { BUSINESS_TIME_ZONE, LOCALE } from '../config/regional';

const CALENDAR_DATE = /^\d{4}-\d{2}-\d{2}$/;

const calendarFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const timestampFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: BUSINESS_TIME_ZONE,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZoneName: 'short',
});

/** `2025-12-31` → `31/12/2025`, the same calendar day in every time zone. */
export function formatCalendarDate(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }
  if (!CALENDAR_DATE.test(value)) {
    return value;
  }
  return calendarFormatter.format(new Date(`${value}T00:00:00Z`));
}

/** ISO-8601 UTC timestamp → date and time in `America/Mexico_City`. */
export function formatTimestamp(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }
  const instant = new Date(value);
  return Number.isNaN(instant.getTime()) ? value : timestampFormatter.format(instant);
}
