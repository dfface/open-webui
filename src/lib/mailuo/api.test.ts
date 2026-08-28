import { afterEach, describe, expect, test, vi } from 'vitest';

import { answerMailuo, getMailuoFacets, getMailuoKnowledges, searchMailuo } from './api';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('Mailuo API client', () => {
	test('sends authenticated search request and returns the response contract', async () => {
		const response = {
			requested_mode: 'hybrid',
			executed_mode: 'hybrid',
			degraded: false,
			warnings: [],
			results: []
		};
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(JSON.stringify(response), {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);

		const result = await searchMailuo('token-1', {
			query: '统一搜索',
			mode: 'hybrid',
			knowledge_ids: ['kb-1'],
			sources: ['outline'],
			limit: 20
		});

		expect(result).toEqual(response);
		expect(fetchMock).toHaveBeenCalledOnce();
		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toMatch(/\/api\/v1\/mailuo\/search$/);
		expect(init.headers.authorization).toBe('Bearer token-1');
		expect(JSON.parse(init.body)).toEqual({
			query: '统一搜索',
			mode: 'hybrid',
			knowledge_ids: ['kb-1'],
			sources: ['outline'],
			limit: 20
		});
	});

	test('loads knowledge and facets using their declared methods', async () => {
		const fetchMock = vi
			.fn()
			.mockResolvedValueOnce(
				new Response(JSON.stringify([{ id: 'kb-1', name: '脉络', description: '' }]), {
					status: 200
				})
			)
			.mockResolvedValueOnce(
				new Response(
					JSON.stringify({
						sources: [{ source: 'future_source', display_name: 'future_source', object_count: 1 }]
					}),
					{ status: 200 }
				)
			);
		vi.stubGlobal('fetch', fetchMock);

		await getMailuoKnowledges('token-1');
		await getMailuoFacets('token-1', ['kb-1']);

		expect(fetchMock.mock.calls[0][1].method).toBe('GET');
		expect(fetchMock.mock.calls[1][1].method).toBe('POST');
		expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ knowledge_ids: ['kb-1'] });
	});

	test('starts an authenticated answer stream with the user selected model', async () => {
		const response = new Response('data: [DONE]\n\n', {
			status: 200,
			headers: { 'Content-Type': 'text/event-stream' }
		});
		const fetchMock = vi.fn().mockResolvedValue(response);
		vi.stubGlobal('fetch', fetchMock);

		const [stream, controller] = await answerMailuo('token-1', {
			query: '怎么维护统一搜索？',
			model: 'qwen3',
			mode: 'hybrid',
			knowledge_ids: ['kb-1'],
			sources: ['outline']
		});

		expect(stream).toBe(response);
		expect(controller).toBeInstanceOf(AbortController);
		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toMatch(/\/api\/v1\/mailuo\/answer$/);
		expect(init.headers.authorization).toBe('Bearer token-1');
		expect(JSON.parse(init.body)).toEqual({
			query: '怎么维护统一搜索？',
			model: 'qwen3',
			mode: 'hybrid',
			knowledge_ids: ['kb-1'],
			sources: ['outline']
		});
	});

	test('throws the safe API detail message for non-success responses', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue(
				new Response(
					JSON.stringify({
						detail: { message: 'Mailuo search is temporarily unavailable', request_id: 'r-1' }
					}),
					{ status: 503 }
				)
			)
		);

		await expect(
			searchMailuo('token-1', {
				query: 'x',
				mode: 'hybrid',
				limit: 20
			})
		).rejects.toThrow('Mailuo search is temporarily unavailable');
	});
});
