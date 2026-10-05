import { Link, useParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type {
  ProductDetail,
  RecommendationDetail,
  RecommendationExplanation,
} from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { CodeList } from '../../components/CodeList';
import { ErrorState } from '../../components/ErrorState';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { ProvenancePanel } from '../../components/provenance/ProvenancePanel';
import { QueryView } from '../../components/QueryView';
import { formatCalendarDate } from '../../format/dates';
import { PATHS, toProduct } from '../../routes/paths';
import { CalculationBreakdown } from './CalculationBreakdown';
import { ExplanationPanel } from './ExplanationPanel';
import { outcomeLabel } from './vocabulary';

function DetailBody({ detail }: { detail: RecommendationDetail }) {
  const explanation = useApiQuery<RecommendationExplanation>(API_PATHS.explanation(detail.id));
  // Units always visible: the evaluation does not carry the unit of measure; the product does.
  const product = useApiQuery<ProductDetail>(API_PATHS.product(detail.product.id));
  const unit = product.data?.unit_of_measure ?? null;
  const facts = explanation.data?.facts ?? [];

  return (
    <>
      <h1 className="page__title">
        {outcomeLabel(detail.outcome)} · {detail.product.sku}
      </h1>
      <ProvenancePanel provenance={detail.provenance} />
      <section className="section" aria-labelledby="evaluacion">
        <h2 id="evaluacion" className="section__title">
          Evaluación
        </h2>
        <dl className="facts">
          <dt>Producto</dt>
          <dd>
            <Link to={toProduct(detail.product.id)}>
              {detail.product.sku} · {detail.product.name}
            </Link>
          </dd>
          <dt>Proveedor sugerido</dt>
          <dd>
            {detail.supplier ? `${detail.supplier.name} (${detail.supplier.code})` : 'ninguno'}
          </dd>
          <dt>Resultado</dt>
          <dd>
            {outcomeLabel(detail.outcome)} <code>{detail.outcome}</code>
          </dd>
          <dt>Fecha sugerida de pedido</dt>
          <dd>{formatCalendarDate(detail.suggested_order_date)}</dd>
          <dt>Motivos</dt>
          <dd>
            <CodeList codes={detail.reasons} />
          </dd>
          <dt>Marcas</dt>
          <dd>
            <CodeList codes={detail.flags} />
          </dd>
          <dt>Parámetros de política faltantes</dt>
          <dd>
            <CodeList codes={detail.missing_policy_parameters} />
          </dd>
        </dl>
      </section>

      {explanation.isPending ? (
        <LoadingSkeleton lines={4} label="Cargando la explicación…" />
      ) : null}
      {explanation.isError ? (
        <ErrorState error={explanation.error} onRetry={() => void explanation.refetch()} />
      ) : null}
      {explanation.data ? <ExplanationPanel explanation={explanation.data} /> : null}

      <CalculationBreakdown
        facts={facts}
        inputs={detail.calculation_inputs}
        unitOfMeasure={unit}
        policySnapshot={detail.policy_snapshot}
        engineVersion={detail.engine_version}
        generatedAt={detail.generated_at}
      />
    </>
  );
}

export function RecommendationDetailPage() {
  const { recommendationId = '' } = useParams();
  const result = useApiQuery<RecommendationDetail>(API_PATHS.recommendation(recommendationId));
  return (
    <article className="page">
      <p className="breadcrumb">
        <Link to={PATHS.recommendations}>Recomendaciones</Link>
      </p>
      <QueryView query={result}>{(detail) => <DetailBody detail={detail} />}</QueryView>
    </article>
  );
}
