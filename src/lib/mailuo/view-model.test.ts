import { describe, expect, test } from 'vitest';

import {
	excerptAroundQuery,
	highlightMailuoText,
	resultsForState,
	safeSourceUrl,
	sourceLabel,
	visibleMatches
} from './view-model';
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

	test('puts the literal keyword match first and excerpts around the evidence', () => {
		const keywordResult = {
			...result,
			matches: [
				{ chunk_no: 0, content: '开头没有相关内容。'.repeat(30), matched_by: ['trigram'] },
				{
					chunk_no: 1,
					content: `${'背景说明。'.repeat(30)}这里介绍系统架构以及关键组件。${'后续内容。'.repeat(30)}`,
					matched_by: ['fulltext']
				}
			]
		};
		const [match] = visibleMatches(keywordResult, false, '架构', 'keyword');
		expect(match.chunk_no).toBe(1);
		expect(match.content).toContain('系统架构');
		expect(match.content.startsWith('…')).toBe(true);
	});

	test('splits highlighted text without injecting markup', () => {
		expect(highlightMailuoText('系统架构与架构设计', '架构')).toEqual([
			{ text: '系统', highlighted: false },
			{ text: '架构', highlighted: true },
			{ text: '与', highlighted: false },
			{ text: '架构', highlighted: true },
			{ text: '设计', highlighted: false }
		]);
		expect(excerptAroundQuery('<script>alert(1)</script> 架构', '架构')).toContain('<script>');
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
