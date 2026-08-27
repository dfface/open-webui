import type { MailuoQueryState, MailuoSearchMode } from './types';

const SEARCH_MODES = new Set<MailuoSearchMode>(['hybrid', 'keyword', 'semantic']);

const uniqueValues = (values: string[]) => [
	...new Set(values.map((value) => value.trim()).filter(Boolean))
];

export const parseMailuoQueryState = (url: URL): MailuoQueryState => {
	const rawMode = url.searchParams.get('mode') as MailuoSearchMode | null;
	return {
		query: (url.searchParams.get('q') ?? '').trim(),
		mode: rawMode && SEARCH_MODES.has(rawMode) ? rawMode : 'hybrid',
		knowledgeIds: uniqueValues(url.searchParams.getAll('knowledge')),
		sources: uniqueValues(url.searchParams.getAll('source'))
	};
};

export const serializeMailuoQueryState = (state: MailuoQueryState): string => {
	const params = new URLSearchParams();
	const query = state.query.trim();
	if (query) params.set('q', query);
	params.set('mode', SEARCH_MODES.has(state.mode) ? state.mode : 'hybrid');
	for (const knowledgeId of uniqueValues(state.knowledgeIds)) {
		params.append('knowledge', knowledgeId);
	}
	for (const source of uniqueValues(state.sources)) {
		params.append('source', source);
	}
	return params.toString();
};
