import { describe, expect, test } from 'vitest';

import { parseMailuoQueryState, serializeMailuoQueryState } from './query-state';

describe('Mailuo query URL state', () => {
	test('round-trips Chinese query, mode, knowledges and dynamic sources', () => {
		const query = serializeMailuoQueryState({
			query: '统一搜索 中文',
			mode: 'semantic',
			sort: 'updated_desc',
			knowledgeIds: ['kb-2', 'kb-1'],
			sources: ['memos', 'future_source']
		});

		const parsed = parseMailuoQueryState(new URL(`https://example.test/mailuo?${query}`));

		expect(parsed).toEqual({
			query: '统一搜索 中文',
			mode: 'semantic',
			sort: 'updated_desc',
			knowledgeIds: ['kb-2', 'kb-1'],
			sources: ['memos', 'future_source']
		});
	});

	test('uses safe defaults and removes duplicate or blank filters', () => {
		const parsed = parseMailuoQueryState(
			new URL(
				'https://example.test/mailuo?q=%20test%20&mode=invalid&sort=invalid&knowledge=kb-1&knowledge=kb-1&source=&source=outline'
			)
		);

		expect(parsed).toEqual({
			query: 'test',
			mode: 'hybrid',
			sort: 'relevance',
			knowledgeIds: ['kb-1'],
			sources: ['outline']
		});
	});
});
