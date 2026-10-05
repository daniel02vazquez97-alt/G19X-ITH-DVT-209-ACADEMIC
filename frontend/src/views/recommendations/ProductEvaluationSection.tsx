import { Link } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { RecommendationDetail } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { CodeList } from '../../components/CodeList';
import { QueryView } from '../../components/QueryView';
import { formatCalendarDate } from '../../format/dates';
import { formatQuantity } from '../../format/numbers';
import { toRecommendation } from '../../routes/paths';
import { outcomeLabel } from './vocabulary';

interface ProductEvaluationSectionProps {
  productId: number;
  unitOfMeasure: string;
}

/** Evaluation of the product in the latest recommendation run, whatever its outcome (F7c). */
export function ProductEvaluationSection({
  productId,
  unitOfMeasure,
}: ProductEvaluationSectionProps) {
  const result = useApiQuery<RecommendationDetail>(API_PATHS.productRecommendation(productId));
  return (
    <section className="section" aria-labelledby="producto-evaluacion">
      <h2 id="producto-evaluacion" className="section__title">
        Evaluación del motor
      </h2>
      <QueryView query={result} loadingLines={2}>
        {(detail) => (
          <>
            <dl className="facts">
              <dt>Resultado</dt>
              <dd>
                {outcomeLabel(detail.outcome)} <code>{detail.outcome}</code>
              </dd>
              <dt>Cantidad sugerida</dt>
              <dd>{formatQuantity(detail.recommended_quantity, unitOfMeasure)}</dd>
              <dt>Fecha sugerida de pedido</dt>
              <dd>{formatCalendarDate(detail.suggested_order_date)}</dd>
              <dt>Corte</dt>
              <dd>{formatCalendarDate(detail.as_of_date)}</dd>
              <dt>Motivos</dt>
              <dd>
                <CodeList codes={detail.reasons} />
              </dd>
            </dl>
            <Link to={toRecommendation(detail.id)}>Ver el desglose y la explicación</Link>
          </>
        )}
      </QueryView>
    </section>
  );
}
