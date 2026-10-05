import type { ProductForecast } from '../../api/types';
import { formatCalendarDate } from '../../format/dates';
import { formatDisplay, formatExact } from '../../format/numbers';

type Period = ProductForecast['periods'][number];

interface ForecastTableProps {
  periods: readonly Period[];
  caption: string;
}

export function ForecastTable({ periods, caption }: ForecastTableProps) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Desde</th>
            <th scope="col">Hasta (excluido)</th>
            <th scope="col" className="numeric">
              Predicción
            </th>
            <th scope="col" className="numeric">
              Banda inferior
            </th>
            <th scope="col" className="numeric">
              Banda superior
            </th>
            <th scope="col" className="numeric">
              Nivel nominal
            </th>
            <th scope="col">Método</th>
            <th scope="col">Confianza</th>
          </tr>
        </thead>
        <tbody>
          {periods.map((period) => (
            <tr key={period.period_start}>
              <td>{formatCalendarDate(period.period_start)}</td>
              <td>{formatCalendarDate(period.period_end)}</td>
              <td className="numeric">{formatDisplay(period.predicted_quantity)}</td>
              <td className="numeric">{formatDisplay(period.lower_bound)}</td>
              <td className="numeric">{formatDisplay(period.upper_bound)}</td>
              <td className="numeric">{formatExact(period.confidence_level)}</td>
              <td>
                <code>{period.method_used}</code>
              </td>
              <td>
                <code>{period.confidence_flag}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const INSUFFICIENT_HISTORY = 'INSUFFICIENT_HISTORY';

export function hasInsufficientHistory(periods: readonly Period[]): boolean {
  return periods.some((period) => period.confidence_flag === INSUFFICIENT_HISTORY);
}

export function InsufficientHistoryNotice() {
  return (
    <p className="notice" role="note">
      <strong>Aviso:</strong> historia insuficiente (<code>{INSUFFICIENT_HISTORY}</code>). La
      predicción se apoya en pocos datos y debe leerse con cautela.
    </p>
  );
}

export function NominalBandNote() {
  return (
    <p className="page__note">
      La banda es <strong>nominal</strong>: es el nivel que declara el método (
      <code>confidence_level</code>), no una cobertura validada (US-055, Fase 5).
    </p>
  );
}
