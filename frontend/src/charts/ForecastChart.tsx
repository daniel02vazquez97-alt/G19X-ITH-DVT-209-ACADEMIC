import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts';
import type { ProductForecast } from '../api/types';
import { formatCalendarDate } from '../format/dates';
import { formatDisplay, formatExact } from '../format/numbers';
import { chartCoordinate } from './chartValues';

type Period = ProductForecast['periods'][number];

interface Row {
  label: string;
  predicted: number;
  band: [number, number];
  period: Period;
}

function toRow(period: Period): Row {
  return {
    label: formatCalendarDate(period.period_start),
    predicted: chartCoordinate(period.predicted_quantity),
    band: [chartCoordinate(period.lower_bound), chartCoordinate(period.upper_bound)],
    period,
  };
}

function ExactTooltip({ active, payload }: TooltipContentProps) {
  const row = payload?.[0]?.payload as Row | undefined;
  if (!active || !row) {
    return null;
  }
  const { period } = row;
  return (
    <div className="chart-tooltip">
      <strong>
        {formatCalendarDate(period.period_start)} – {formatCalendarDate(period.period_end)}
      </strong>
      <br />
      Predicción: {formatDisplay(period.predicted_quantity)}
      <br />
      Banda: {formatDisplay(period.lower_bound)} – {formatDisplay(period.upper_bound)}
    </div>
  );
}

interface ForecastChartProps {
  periods: readonly Period[];
  unit: string;
}

/**
 * Forecast with its nominal band (DT-070 point 12). The table next to it is the textual alternative
 * of the chart; the chart itself is hidden from assistive technology.
 */
export function ForecastChart({ periods, unit }: ForecastChartProps) {
  const rows = periods.map(toRow);
  const level = periods[0] ? formatExact(periods[0].confidence_level) : '';
  return (
    <figure className="chart">
      <div aria-hidden="true">
        <ComposedChart
          responsive
          data={rows}
          style={{ width: '100%', height: 320 }}
          margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={72} />
          <Tooltip content={ExactTooltip} />
          <Legend />
          <Area
            dataKey="band"
            name={`Banda nominal ${level}`}
            stroke="none"
            fill="var(--color-accent-soft)"
            isAnimationActive={false}
          />
          <Line
            dataKey="predicted"
            name="Predicción"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </div>
      <figcaption className="page__note">
        Predicción semanal en {unit} con su banda nominal {level}; los valores exactos están en la
        tabla.
      </figcaption>
    </figure>
  );
}
