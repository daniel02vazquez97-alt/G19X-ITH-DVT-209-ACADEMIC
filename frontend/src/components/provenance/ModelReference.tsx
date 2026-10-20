import type { ModelRef } from '../../api/types';

/**
 * Reference model of a forecast (DT-057) and, since U14, the Azure ML registry entry it was validated and
 * registered under (DT-102, DT-104). The interface only shows what the API stored; it never asks Azure ML.
 */
export function ModelReference({ model }: { model: ModelRef | null | undefined }) {
  if (!model) {
    return <>—</>;
  }
  return (
    <>
      {`${model.name} ${model.version}`}
      {model.external_ref ? (
        <>
          {' · registrado y validado en Azure ML como '}
          <code>{model.external_ref}</code>
        </>
      ) : null}
    </>
  );
}
