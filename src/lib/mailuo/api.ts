import { WEBUI_API_BASE_URL } from '$lib/constants';

import type {
	MailuoFacetResponse,
	MailuoAnswerRequest,
	MailuoKnowledge,
	MailuoSearchRequest,
	MailuoSearchResponse
} from './types';

const MAILUO_API_URL = `${WEBUI_API_BASE_URL}/mailuo`;

const errorMessage = (payload: unknown): string => {
	if (!payload || typeof payload !== 'object') return 'Mailuo request failed';
	const detail = (payload as { detail?: unknown }).detail;
	if (typeof detail === 'string') return detail;
	if (detail && typeof detail === 'object' && 'message' in detail) {
		const message = (detail as { message?: unknown }).message;
		if (typeof message === 'string') return message;
	}
	return 'Mailuo request failed';
};

const request = async <T>(token: string, path: string, init: RequestInit): Promise<T> => {
	const response = await fetch(`${MAILUO_API_URL}${path}`, {
		...init,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`,
			...init.headers
		}
	});
	const payload = await response.json().catch(() => null);
	if (!response.ok) throw new Error(errorMessage(payload));
	return payload as T;
};

export const getMailuoKnowledges = (token: string) =>
	request<MailuoKnowledge[]>(token, '/knowledges', { method: 'GET' });

export const getMailuoFacets = (token: string, knowledgeIds?: string[]) =>
	request<MailuoFacetResponse>(token, '/facets', {
		method: 'POST',
		body: JSON.stringify({ knowledge_ids: knowledgeIds?.length ? knowledgeIds : null })
	});

export const searchMailuo = (token: string, payload: MailuoSearchRequest) =>
	request<MailuoSearchResponse>(token, '/search', {
		method: 'POST',
		body: JSON.stringify(payload)
	});

export const answerMailuo = async (
	token: string,
	payload: MailuoAnswerRequest
): Promise<[Response, AbortController]> => {
	const controller = new AbortController();
	const response = await fetch(`${MAILUO_API_URL}/answer`, {
		method: 'POST',
		signal: controller.signal,
		headers: {
			Accept: 'text/event-stream',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw new Error(errorMessage(body));
	}
	return [response, controller];
};
