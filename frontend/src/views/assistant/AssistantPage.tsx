// Documentary assistant (U15b, DT-103): a question about the synthetic documents of the project, answered by the API
// with Azure AI Search (fragments filtered by the roles' groups) and the U13 model, always with its sources. The
// question lives in the URL (DT-070 point 2). It does not decide purchases or change recommendations.
import { useId, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { AssistantAnswer } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { NoticeBanner } from '../../components/NoticeBanner';
import { QueryView } from '../../components/QueryView';

const MIN = 3;
const MAX = 300;

const STATUS_TEXTS: Record<AssistantAnswer['status'], string> = {
  ANSWERED: 'Respuesta redactada por el modelo con los fragmentos recuperados',
  RETRIEVAL_ONLY: 'Solo fragmentos: sin respuesta redactada por el modelo',
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (text.length >= MIN) {
      setSearch({ pregunta: text });
    }
  }

  return (
    <article className="page">
      <h1 className="page__title">Asistente documental</h1>
      <p className="page__note">
        Responde con los documentos sintéticos del proyecto: busca los fragmentos en Azure AI Search
        y el modelo de Azure OpenAI redacta la respuesta citándolos. No decide compras ni cambia
        recomendaciones.
      </p>
      <form
        className="filters"
        aria-label="Pregunta al asistente"
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="filters__field">
          <label htmlFor={inputId} className="field__label">
            Pregunta
          </label>
          <textarea
            id={inputId}
            name="pregunta"
            className="field__input"
            rows={3}
            maxLength={MAX}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </div>
        <button
          type="submit"
          className="button button--primary"
          disabled={draft.trim().length < MIN}
        >
          Preguntar
        </button>
      </form>
      {valid ? (
        <QueryView query={result}>{(answer) => <AnswerView answer={answer} />}</QueryView>
      ) : null}
    </article>
  );
}

function AnswerView({ answer }: { answer: AssistantAnswer }) {
  return (
    <>
      <NoticeBanner notices={answer.notices} />
      <section className="section" aria-labelledby="respuesta">
        <h2 id="respuesta" className="section__title">
          Respuesta
        </h2>
        <p className="narrative">{answer.answer}</p>
        <p className="page__note">
          {STATUS_TEXTS[answer.status]} · modelo: <code>{answer.generator ?? 'ninguno'}</code> ·
          recuperador: <code>{answer.retriever}</code>
        </p>
        {answer.warning ? (
          <div className="notice" role="status">
            <p className="notice__title">{WARNING_TEXTS[answer.warning]}</p>
          </div>
        ) : null}
      </section>
      {answer.citations.length > 0 ? (
        <section className="section" aria-labelledby="fuentes">
          <h2 id="fuentes" className="section__title">
            Fuentes
          </h2>
          <ol>
            {answer.citations.map((citation) => (
              <li key={citation.number} value={citation.number}>
                <strong>{citation.title}</strong> — {citation.section}
                {citation.cited ? ' (citada en la respuesta)' : null}
                <blockquote>{citation.excerpt}</blockquote>
                <code>{citation.source_url}</code>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </>
  );
}
