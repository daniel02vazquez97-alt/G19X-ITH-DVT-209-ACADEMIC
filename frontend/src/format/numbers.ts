// Presentation of the exact numbers of the API (DT-069, DT-070 points 15 and 22). Values arrive as
// text (integer, decimal, 28-digit `Decimal` or rational `"p/q"`) and are never turned into floats.
// No thousands separator, so that figures match the verified narrative of U6 character by character.
// This module only presents values; it never feeds a decision.

const DISPLAY_DECIMALS = 6;
const DISPLAY_SCALE = 10n ** BigInt(DISPLAY_DECIMALS);

const INTEGER = /^-?\d+$/;
const DECIMAL = /^(-?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/;
const RATIONAL = /^(-?\d+)\/(\d+)$/;

export const NOT_CALCULATED = 'no calculado';

/** Exact representation as the backend sends it (technical details of the breakdown). */
export function formatExact(value: string | null | undefined): string {
  return value === null || value === undefined ? NOT_CALCULATED : value;
}

function abs(value: bigint): bigint {
  return value < 0n ? -value : value;
}

/** `numerator / denominator` rounded to an integer, ties to even (`ROUND_HALF_EVEN`). */
function divideHalfEven(numerator: bigint, denominator: bigint): bigint {
  const negative = numerator < 0n !== denominator < 0n;
  const n = abs(numerator);
  const d = abs(denominator);
  let quotient = n / d;
  const twiceRemainder = (n % d) * 2n;
  if (twiceRemainder > d || (twiceRemainder === d && quotient % 2n === 1n)) {
    quotient += 1n;
  }
  return negative ? -quotient : quotient;
}

/** Fixed-point text of `scaled / 10^6` without trailing zeros; `0` is never negative. */
function fixedText(scaled: bigint): string {
  if (scaled === 0n) {
    return '0';
  }
  const digits = abs(scaled)
    .toString()
    .padStart(DISPLAY_DECIMALS + 1, '0');
  const integerPart = digits.slice(0, -DISPLAY_DECIMALS);
  const fraction = digits.slice(-DISPLAY_DECIMALS).replace(/0+$/, '');
  return `${scaled < 0n ? '-' : ''}${integerPart}${fraction ? `.${fraction}` : ''}`;
}

/** Decimal text as `scaled / 10^6`, rounded half to even. `null` if it is not a decimal. */
function scaleDecimal(value: string): bigint | null {
  const match = DECIMAL.exec(value);
  if (!match) {
    return null;
  }
  const [, sign = '', whole = '', fraction = '', exponentText = '0'] = match;
  if (whole === '' && fraction === '') {
    return null;
  }
  const exponent = BigInt(exponentText);
  const mantissa = BigInt(`${sign}${whole}${fraction}` || '0');
  // value = mantissa * 10^(exponent - fraction.length); scaled = value * 10^6.
  const shift = exponent - BigInt(fraction.length) + BigInt(DISPLAY_DECIMALS);
  return shift >= 0n ? mantissa * 10n ** shift : divideHalfEven(mantissa, 10n ** -shift);
}

/**
 * `display` rule of DT-069 for a value that the API sends without its own `display`: integers
 * normalized (`-0` → `0`); decimals and `"p/q"` with 6 decimals `ROUND_HALF_EVEN` and no trailing zeros. Text that
 * is not a number is returned unchanged.
 */
export function formatDisplay(value: string): string {
  if (INTEGER.test(value)) {
    // Like the backend: `-0` is `0` and leading zeros go away.
    return BigInt(value).toString();
  }
  const rational = RATIONAL.exec(value);
  if (rational) {
    const [, numerator = '0', denominator = '1'] = rational;
    if (BigInt(denominator) === 0n) {
      return value;
    }
    return fixedText(divideHalfEven(BigInt(numerator) * DISPLAY_SCALE, BigInt(denominator)));
  }
  const scaled = scaleDecimal(value);
  return scaled === null ? value : fixedText(scaled);
}

/** A quantity with its unit always visible (DT-070 point 6). */
export function formatQuantity(value: string | null | undefined, unit: string): string {
  return value === null || value === undefined ? NOT_CALCULATED : `${formatDisplay(value)} ${unit}`;
}
