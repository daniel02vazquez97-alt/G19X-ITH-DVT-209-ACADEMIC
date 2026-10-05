import { describe, expect, it } from 'vitest';
import { formatCalendarDate, formatTimestamp } from './dates';

describe('dates (es-MX, America/Mexico_City)', () => {
  it('shows a calendar date without time-zone conversion', () => {
    expect(formatCalendarDate('2025-12-31')).toBe('31/12/2025');
    expect(formatCalendarDate('2026-01-01')).toBe('01/01/2026');
  });

  it('converts a UTC timestamp to Mexico City time', () => {
    // 2026-01-01T03:30:00Z is still 31/12/2025 21:30 in Mexico City (UTC-6).
    const text = formatTimestamp('2026-01-01T03:30:00Z');
    expect(text).toContain('31/12/2025');
    expect(text).toContain('21:30');
  });

  it('keeps unexpected text and shows a dash for missing values', () => {
    expect(formatCalendarDate('31-12-2025')).toBe('31-12-2025');
    expect(formatTimestamp('no-date')).toBe('no-date');
    expect(formatCalendarDate(null)).toBe('—');
    expect(formatTimestamp(undefined)).toBe('—');
  });
});
