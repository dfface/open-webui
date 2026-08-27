import { describe, expect, test } from 'vitest';

import { resultsForState, safeSourceUrl, sourceLabel, visibleMatches } from './view-model';
import type { MailuoObjectResult } from './types';

const result: MailuoObjectResult = {
	knowledge_ids: ['kb-1'],
	source: 'future_source',
	source_object_id: 'object-1',
	title: 'Future',
	source_url: 'https://future.example/object/1',
	source_updated_at: '2026-08-27T00:00:00Z',
	metadata: {},
	matched_by: ['semantic'],
	matches: [
		{ chunk_no: 0, content: 'one', matched_by: ['semantic'] },
		{ chunk_no: 1, content: 'two', matched_by: ['trigram'] },
		{ chunk_no: 2, content: 'three', matched_by: ['fulltext'] }
	]
};

describe('Mailuo result view model', () => {
	test('keeps current results while loading and applies completed results', () => {
		expect(resultsForState([result], [], true)).toEqual([result]);
		expect(resultsForState([result], [], false)).toEqual([]);
	});

	test('shows one snippet by default and no more than three when expanded', () => {
		expect(visibleMatches(result, false)).toEqual([result.matches[0]]);
		expect(visibleMatches(result, true)).toEqual(result.matches);
	});

	test('falls back to an unknown source key and only accepts safe absolute links', () => {
		expect(sourceLabel('future_source', new Map())).toBe('future_source');
		expect(safeSourceUrl('https://future.example/object/1')).toBe(
			'https://future.example/object/1'
		);
		expect(safeSourceUrl('javascript:alert(1)')).toBeNull();
		expect(safeSourceUrl('/relative/path')).toBeNull();
	});
});
