import { describe, expect, it } from 'vitest';
import { formatDisplay, formatExact, formatQuantity, NOT_CALCULATED } from './numbers';

describe('formatExact', () => {
  it.each([
    '2623.500600092591729239380374',
    '1.225403763305688728630637860',
    '238877404/109375',
    '-8',
    '0',
  ])('keeps %s character by character', (value) => {
    expect(formatExact(value)).toBe(value);
  });

  it('shows a null term as "no calculado"', () => {
    expect(formatExact(null)).toBe(NOT_CALCULATED);
  });
});

describe('formatDisplay (DT-069 rule)', () => {
  it.each([
    // Values of the real run (backend/tests/genai/_genai_fixtures.py) and their hand-computed displays.
    ['2700', '2700'],
    ['-8', '-8'],
    ['-0', '0'],
    ['007', '7'],
    ['265346154/109375', '2426.021979'],
    ['439.4786206640203006679518026', '439.478621'],
    ['2623.500600092591729239380374', '2623.5006'],
    ['78.02191620945438640224055247', '78.021916'],
    ['2.021916209454386402240552468', '2.021916'],
    ['132673077/70000', '1895.329671'],
    ['1.65', '1.65'],
    // Ties go to the even neighbour; nothing becomes "-0".
    ['0.0000005', '0'],
    ['0.0000015', '0.000002'],
    ['0.0000025', '0.000002'],
    ['-0.0000004', '0'],
    ['-2.5000005', '-2.5'],
    ['1/3', '0.333333'],
    ['2/3', '0.666667'],
    ['-1/8', '-0.125'],
    ['5.000000', '5'],
    ['1E+3', '1000'],
    ['0E-28', '0'],
  ])('%s → %s', (value, expected) => {
    expect(formatDisplay(value)).toBe(expected);
  });

  it('keeps 28 significant digits exact before rounding (no float)', () => {
    // As a float, 0.1000005 would be 0.10000049999…, which rounds down.
    expect(formatDisplay('0.1000005000000000000000000001')).toBe('0.100001');
    expect(formatDisplay('9999999999999999999999.9999995')).toBe('10000000000000000000000');
  });

  it('returns text that is not a number unchanged', () => {
    expect(formatDisplay('OBSERVED')).toBe('OBSERVED');
    expect(formatDisplay('1/0')).toBe('1/0');
  });

  it('never uses a thousands separator', () => {
    expect(formatDisplay('1234567.5')).toBe('1234567.5');
  });
});

describe('formatQuantity', () => {
  it('always shows the unit', () => {
    expect(formatQuantity('2623.500600092591729239380374', 'BOX')).toBe('2623.5006 BOX');
    expect(formatQuantity(null, 'KG')).toBe(NOT_CALCULATED);
  });
});
