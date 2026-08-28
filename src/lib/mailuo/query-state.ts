import type { MailuoQueryState, MailuoSearchMode, MailuoSearchSort } from './types';

const SEARCH_MODES = new Set<MailuoSearchMode>(['hybrid', 'keyword', 'semantic']);
const SEARCH_SORTS = new Set<MailuoSearchSort>(['relevance', 'updated_desc', 'updated_asc']);

const uniqueValues = (values: string[]) => [
	...new Set(values.map((value) => value.trim()).filter(Boolean))
];

export const parseMailuoQueryState = (url: URL): MailuoQueryState => {
	const rawMode = url.searchParams.get('mode') as MailuoSearchMode | null;
	const rawSort = url.searchParams.get('sort') as MailuoSearchSort | null;
	return {
		query: (url.searchParams.get('q') ?? '').trim(),
		mode: rawMode && SEARCH_MODES.has(rawMode) ? rawMode : 'hybrid',
		sort: rawSort && SEARCH_SORTS.has(rawSort) ? rawSort : 'relevance',
		knowledgeIds: uniqueValues(url.searchParams.getAll('knowledge')),
		sources: uniqueValues(url.searchParams.getAll('source'))
	};
};

export const serializeMailuoQueryState = (state: MailuoQueryState): string => {
	const params = new URLSearchParams();
	const query = state.query.trim();
	if (query) params.set('q', query);
	params.set('mode', SEARCH_MODES.has(state.mode) ? state.mode : 'hybrid');
	if (state.sort !== 'relevance') {
		params.set('sort', SEARCH_SORTS.has(state.sort) ? state.sort : 'relevance');
	}
	for (const knowledgeId of uniqueValues(state.knowledgeIds)) {
		params.append('knowledge', knowledgeId);
	}
	for (const source of uniqueValues(state.sources)) {
		params.append('source', source);
	}
	return params.toString();
};
