// DT-070 point 8 and `docs/08` §7: the interface never recalculates. This test reads the source of
// the application and fails if it finds numeric conversion, float arithmetic or business formulas.
import { describe, expect, it } from 'vitest';

const sources = import.meta.glob<string>(
  ['../**/*.{ts,tsx}', '!../**/*.test.{ts,tsx}', '!../test/**'],
  {
    query: '?raw',
    import: 'default',
    eager: true,
  },
);

/** Presentation rounding of DT-069 / DT-070 point 22, the only place allowed to use `BigInt`. */
const DISPLAY_MODULE = '../format/numbers.ts';

/** Chart geometry (Recharts needs numbers), the only place allowed to use `Number()`. */
const CHART_MODULE = '../charts/chartValues.ts';

const FORBIDDEN: Array<[string, RegExp]> = [
  ['parseFloat', /\bparseFloat\b/],
  ['parseInt', /\bparseInt\b/],
  ['Math', /\bMath\./],
  ['toFixed / toPrecision', /\.(toFixed|toPrecision)\s*\(/],
  ['unary plus conversion', /[=(,:]\s*\+\s*[A-Za-z_$]/],
  ['business vocabulary', /\b(coverage|urgency|riskLevel|reorderPoint|safetyStock|daysOfCover)\b/],
  ['reading a reorder or safety term', /\.(reorder_point|safety_stock|coverage_days)\b/],
];

describe('no business formulas in the client', () => {
  const files = Object.entries(sources).filter(([path]) => !path.endsWith('.gen.ts'));

  it('reads the application sources', () => {
    expect(files.length).toBeGreaterThan(20);
  });

  it.each(FORBIDDEN)('no %s', (_label, pattern) => {
    const offenders = files.filter(([, text]) => pattern.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('Number() only in the chart geometry module', () => {
    const offenders = files
      .filter(([path, text]) => path !== CHART_MODULE && /\bNumber\s*\(/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('chart numbers never reach text: only the chart uses the geometry module', () => {
    const users = files
      .filter(([path, text]) => path !== CHART_MODULE && text.includes('chartValues'))
      .map(([path]) => path);
    expect(users).toEqual(['../charts/ForecastChart.tsx']);
  });

  it('BigInt only in the display module', () => {
    const offenders = files
      .filter(([path, text]) => path !== DISPLAY_MODULE && /\bBigInt\b|\d+n\b/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('no localStorage or sessionStorage', () => {
    const offenders = files
      .filter(([, text]) => /\b(localStorage|sessionStorage)\b/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it('the API base is relative', () => {
    const offenders = files.filter(([, text]) => /https?:\/\//.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
