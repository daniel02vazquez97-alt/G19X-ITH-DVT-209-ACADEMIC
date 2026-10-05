import { API_PATHS } from '../../api/paths';
import type { ProductForecast } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { ForecastChart } from '../../charts/ForecastChart';
import { ProvenancePanel } from '../../components/provenance/ProvenancePanel';
import { QueryView } from '../../components/QueryView';
import {
  ForecastTable,
  hasInsufficientHistory,
  InsufficientHistoryNotice,
  NominalBandNote,
} from './ForecastTable';

interface ProductForecastSectionProps {
  productId: number;
  unitOfMeasure: string;
}

/** Forecast of the product (US-075 partial, DT-070 point 12). A 404 is an empty state. */
export function ProductForecastSection({ productId, unitOfMeasure }: ProductForecastSectionProps) {
  const result = useApiQuery<ProductForecast>(API_PATHS.productForecast(productId));
  return (
    <section className="section" aria-labelledby="producto-forecast">
      <h2 id="producto-forecast" className="section__title">
        Predicción
      </h2>
      <p className="page__note">
        Semanas ancladas en el corte (desde el día siguiente al corte), en {unitOfMeasure}.
      </p>
      <QueryView query={result} loadingLines={4}>
        {(forecast) => (
          <>
            <ProvenancePanel provenance={forecast.provenance} />
            {hasInsufficientHistory(forecast.periods) ? <InsufficientHistoryNotice /> : null}
            <NominalBandNote />
            <ForecastChart periods={forecast.periods} unit={unitOfMeasure} />
            <ForecastTable periods={forecast.periods} caption="Predicción semanal del producto" />
          </>
        )}
      </QueryView>
    </section>
  );
}
