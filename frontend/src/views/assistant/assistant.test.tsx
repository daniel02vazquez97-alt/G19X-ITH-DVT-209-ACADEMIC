import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { errorResponse, installFetch, jsonResponse, requestedUrls, routeApi } from '../../test/api';
import { loginAs, renderApp } from '../../test/renderApp';

const ANSWER = {
  question: '¿El asistente puede decidir qué comprar?',
  answer: 'No: el sistema solo sugiere y una persona decide [1].',
  status: 'ANSWERED',
  warning: null,
  generator: 'azure-openai/gpt-41-mini',
  retriever: 'azure-ai-search',
  citations: [
    {
      number: 1,
      document_id: 'U15-SYN-001',
      title: 'Resumen de la política provisional de inventario',
      section: 'Alcance',
      source_url: 'knowledge/search_corpus/politica-v1.md#alcance',
      excerpt: 'El asistente no decide compras.',
      cited: true,
    },
    {
      number: 2,
      document_id: 'U15-SYN-003',
      title: 'Preguntas frecuentes de demostración',
      section: 'Compras',
      source_url: 'knowledge/search_corpus/preguntas-frecuentes.md#compras',
      excerpt: 'No se ejecutan compras automáticas.',
      cited: false,
    },
  ],
  data_origin: 'SYNTHETIC',
  notices: ['SYNTHETIC_DATA'],
};

describe('AssistantPage (U15b, DT-103)', () => {
  it('asks the API with the question in the URL and shows the answer with its sources', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/assistant/answer': () => jsonResponse(200, ANSWER) }),
    );
    const { user, router } = renderApp('/asistente');
    await loginAs(user, 'VIEWER');
    expect(screen.getByRole('heading', { name: 'Asistente documental' })).toBeInTheDocument();
    expect(requestedUrls(fetchMock)).toEqual([]); // nothing is asked before a question
    await user.type(screen.getByLabelText('Pregunta'), ANSWER.question);
    await user.click(screen.getByRole('button', { name: 'Preguntar' }));
    // The [n] markers are styled, but the text of the answer stays exactly the API's.
    const answer = await screen.findByRole('region', { name: 'Respuesta' });
    expect(answer.querySelector('.answer__text')?.textContent).toBe(ANSWER.answer);
    expect(answer.querySelectorAll('.cite')).toHaveLength(1);
    expect(router.state.location.search).toBe(
      `?${new URLSearchParams({ pregunta: ANSWER.question }).toString()}`,
    );
    expect(requestedUrls(fetchMock)).toEqual([
      `/api/v1/assistant/answer?${new URLSearchParams({ q: ANSWER.question }).toString()}`,
    ]);
    expect(screen.getByText('azure-openai/gpt-41-mini')).toBeInTheDocument();
    expect(screen.getByText('azure-ai-search')).toBeInTheDocument();
    const sources = screen.getByRole('region', { name: 'Fuentes' });
    expect(within(sources).getAllByRole('listitem')).toHaveLength(2);
    expect(within(sources).getByText('El asistente no decide compras.')).toBeInTheDocument();
    expect(within(sources).getAllByText('Citada en la respuesta')).toHaveLength(1);
    expect(screen.getByText(/Datos sintéticos/)).toBeInTheDocument();
  });

  it('shows the fragments and the warning when the model did not answer', async () => {
    const fallback = {
      ...ANSWER,
      answer: 'No se pudo generar la respuesta: estos son los fragmentos más relevantes.',
      status: 'RETRIEVAL_ONLY',
      warning: 'GENERATOR_UNAVAILABLE',
      generator: null,
      retriever: 'local (respaldo)',
      citations: ANSWER.citations.map((citation) => ({ ...citation, cited: false })),
    };
    installFetch(routeApi({ '/api/v1/assistant/answer': () => jsonResponse(200, fallback) }));
    const { user } = renderApp('/asistente?pregunta=compras%20autom%C3%A1ticas');
    await loginAs(user, 'ANALYST');
    expect(await screen.findByText(fallback.answer)).toBeInTheDocument();
    expect(screen.getByText(/El modelo no respondió/)).toBeInTheDocument();
    expect(screen.getByText('ninguno')).toBeInTheDocument();
    expect(screen.getByText('local (respaldo)')).toBeInTheDocument();
  });

  it('a 503 of the assistant is shown with the uniform error state', async () => {
    installFetch(
      routeApi({ '/api/v1/assistant/answer': () => errorResponse(503, 'ASSISTANT_UNAVAILABLE') }),
    );
    const { user } = renderApp('/asistente?pregunta=compras');
    await loginAs(user, 'PLANNER');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('an example question is asked with one click and is kept in the URL', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/assistant/answer': () => jsonResponse(200, ANSWER) }),
    );
    const { user, router } = renderApp('/asistente');
    await loginAs(user, 'VIEWER');
    await user.click(screen.getByRole('button', { name: '¿Esta documentación es real?' }));
    await screen.findByRole('region', { name: 'Respuesta' });
    expect(router.state.location.search).toBe('?pregunta=%C2%BFEsta+documentaci%C3%B3n+es+real%3F');
    expect(screen.getByLabelText('Pregunta')).toHaveValue('¿Esta documentación es real?');
    expect(requestedUrls(fetchMock)).toHaveLength(1);
    expect(screen.queryByRole('region', { name: 'Prueba con una de estas preguntas' })).toBeNull();
  });

  it('a question shorter than 3 characters cannot be sent', async () => {
    installFetch(routeApi({}));
    const { user } = renderApp('/asistente');
    await loginAs(user, 'ADMIN');
    await user.type(screen.getByLabelText('Pregunta'), 'no');
    expect(screen.getByRole('button', { name: 'Preguntar' })).toBeDisabled();
  });
});
