// Documentary assistant (U15b, DT-103): a question about the synthetic documents of the project, answered by the API
// with Azure AI Search (fragments filtered by the roles' groups) and the U13 model, always with its sources. The
// question lives in the URL (DT-070 point 2). It does not decide purchases or change recommendations.
import { useId, useState, type FormEvent, type ReactNode } from 'react';
import { useSearchParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { AssistantAnswer } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { NoticeBanner } from '../../components/NoticeBanner';
import { QueryView } from '../../components/QueryView';

const MIN = 3;
const MAX = 300;

/** Questions the synthetic corpus can answer, offered while nothing has been asked yet. */
const EXAMPLES = [
  '¿El asistente puede decidir qué comprar?',
  '¿De dónde salen las cifras de una recomendación?',
  '¿Esta documentación es real?',
];

const STATUS_LABELS: Record<AssistantAnswer['status'], string> = {
  ANSWERED: 'Redactada por el modelo con los fragmentos recuperados',
  RETRIEVAL_ONLY: 'Solo fragmentos, sin respuesta del modelo',
  NO_DOCUMENTS: 'Sin documentos relacionados',
};

const WARNING_TEXTS: Record<NonNullable<AssistantAnswer['warning']>, string> = {
  GENERATOR_UNAVAILABLE: 'El modelo no respondió; se muestran los fragmentos más relevantes.',
  UNCITED: 'La respuesta no cita ningún fragmento: contrástala con las fuentes.',
};

export function AssistantPage() {
  const [search, setSearch] = useSearchParams();
  const question = (search.get('pregunta') ?? '').trim();
  const [draft, setDraft] = useState(question);
  const inputId = useId();
  const valid = question.length >= MIN && question.length <= MAX;
  const result = useApiQuery<AssistantAnswer>(
    API_PATHS.assistant,
    { q: question },
    { enabled: valid },
  );

  function ask(text: string) {
    setDraft(text);
    setSearch({ pregunta: text });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (text.length >= MIN) {
      ask(text);
    }
  }

  return (
    <article className="page assistant">
      <header className="page__header">
        <h1 className="page__title">Asistente documental</h1>
        <p className="page__lead">
          Responde con los documentos sintéticos del proyecto: busca los fragmentos en Azure AI
          Search y el modelo de Azure OpenAI redacta la respuesta citándolos. No decide compras ni
          cambia recomendaciones.
        </p>
      </header>
      <form
        className="card ask"
        aria-label="Pregunta al asistente"
        onSubmit={handleSubmit}
        noValidate
      >
        <label htmlFor={inputId} className="field__label">
          Pregunta
        </label>
        <textarea
          id={inputId}
          name="pregunta"
          className="field__input ask__input"
          rows={3}
          maxLength={MAX}
          placeholder="Escribe una pregunta sobre la política, los datos o el uso del sistema"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className="ask__footer">
          <span className="ask__count">
            {draft.length} / {MAX}
          </span>
          <button
            type="submit"
            className="button button--primary"
            disabled={draft.trim().length < MIN}
          >
            Preguntar
          </button>
        </div>
      </form>
      {valid ? (
        <QueryView query={result}>{(answer) => <AnswerView answer={answer} />}</QueryView>
      ) : (
        <section className="examples" aria-labelledby="ejemplos">
          <h2 id="ejemplos" className="examples__title">
            Prueba con una de estas preguntas
          </h2>
          <div className="examples__list">
            {EXAMPLES.map((example) => (
              <button key={example} type="button" className="chip" onClick={() => ask(example)}>
                {example}
              </button>
            ))}
          </div>
        </section>
      )}
    </article>
  );
}

/** The answer text with each `[n]` shown as a marker; the text content stays exactly the API's answer. */
function withCitationMarkers(text: string): ReactNode[] {
  return text.split(/(\[\d+\])/).map((part, index) =>
    /^\[\d+\]$/.test(part) ? (
      <span key={index} className="cite">
        <span className="visually-hidden">[</span>
        {part.slice(1, -1)}
        <span className="visually-hidden">]</span>
      </span>
    ) : (
      part
    ),
  );
}

function AnswerView({ answer }: { answer: AssistantAnswer }) {
  return (
    <>
      <NoticeBanner notices={answer.notices} />
      <section className="card answer" aria-labelledby="respuesta">
        <div className="card__header">
          <h2 id="respuesta" className="card__title">
            Respuesta
          </h2>
          <span className={`badge badge--${answer.status.toLowerCase()}`}>
            {STATUS_LABELS[answer.status]}
          </span>
        </div>
        <p className="answer__text">{withCitationMarkers(answer.answer)}</p>
        {answer.warning ? (
          <div className="notice" role="status">
            <p className="notice__title">{WARNING_TEXTS[answer.warning]}</p>
          </div>
        ) : null}
        <dl className="answer__meta">
          <div>
            <dt>Modelo</dt>
            <dd>
              <code>{answer.generator ?? 'ninguno'}</code>
            </dd>
          </div>
          <div>
            <dt>Recuperador</dt>
            <dd>
              <code>{answer.retriever}</code>
            </dd>
          </div>
        </dl>
      </section>
      {answer.citations.length > 0 ? (
        <section className="section" aria-labelledby="fuentes">
          <h2 id="fuentes" className="section__title">
            Fuentes
          </h2>
          <ol className="sources">
            {answer.citations.map((citation) => (
              <li
                key={citation.number}
                value={citation.number}
                className={citation.cited ? 'source source--cited' : 'source'}
              >
                <div className="source__head">
                  <span className="source__number" aria-hidden="true">
                    {citation.number}
                  </span>
                  <div className="source__heading">
                    <strong className="source__title">{citation.title}</strong>
                    <span className="source__section">{citation.section}</span>
                  </div>
                  {citation.cited ? (
                    <span className="badge badge--cited">Citada en la respuesta</span>
                  ) : null}
                </div>
                <blockquote className="source__excerpt">{citation.excerpt}</blockquote>
                <code className="source__path">{citation.source_url}</code>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </>
  );
}
