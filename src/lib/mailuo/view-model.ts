import type { MailuoObjectResult, MailuoSearchMode, MailuoSnippet } from './types';

export type MailuoTextSegment = {
	text: string;
	highlighted: boolean;
};

const queryTerms = (query: string): string[] => {
	const normalized = query.trim();
	if (!normalized) return [];
	const tokens = normalized
		.split(/[\s,，。！？!?;；:：、()[\]{}"'“”‘’]+/u)
		.map((term) => term.trim())
		.filter(Boolean);
	return [...new Set([normalized, ...tokens])].sort((left, right) => right.length - left.length);
};

const literalMatchPosition = (content: string, query: string): number => {
	const normalizedContent = content.toLocaleLowerCase();
	const positions = queryTerms(query)
		.map((term) => normalizedContent.indexOf(term.toLocaleLowerCase()))
		.filter((position) => position >= 0);
	return positions.length ? Math.min(...positions) : -1;
};

export const normalizeMailuoContent = (content: string): string =>
	content
		.replace(/\\r\\n|\\n|\\r/g, '\n')
		.replace(/\n{3,}/g, '\n\n')
		.trim();

export const excerptAroundQuery = (content: string, query: string, maxLength = 260): string => {
	const normalized = normalizeMailuoContent(content);
	if (normalized.length <= maxLength) return normalized;

	const matchPosition = literalMatchPosition(normalized, query);
	if (matchPosition < 0) return `${normalized.slice(0, maxLength).trimEnd()}…`;

	const before = Math.floor(maxLength * 0.35);
	let start = Math.max(0, matchPosition - before);
	let end = Math.min(normalized.length, start + maxLength);
	start = Math.max(0, end - maxLength);

	const boundaries = ['\n', '。', '！', '？', '.', '!', '?', '；', ';'];
	const previousBoundary = Math.max(
		...boundaries.map((mark) => normalized.lastIndexOf(mark, start))
	);
	if (previousBoundary >= 0 && previousBoundary < matchPosition) start = previousBoundary + 1;

	const nextBoundaries = boundaries
		.map((mark) => normalized.indexOf(mark, end))
		.filter((position) => position >= 0 && position - end <= 80);
	if (nextBoundaries.length) end = Math.min(...nextBoundaries) + 1;

	const excerpt = normalized.slice(start, end).trim();
	return `${start > 0 ? '…' : ''}${excerpt}${end < normalized.length ? '…' : ''}`;
};

export const highlightMailuoText = (content: string, query: string): MailuoTextSegment[] => {
	const terms = queryTerms(query);
	if (!terms.length) return [{ text: content, highlighted: false }];

	const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
	const pattern = new RegExp(`(${escaped.join('|')})`, 'giu');
	return content
		.split(pattern)
		.filter(Boolean)
		.map((text) => ({
			text,
			highlighted: terms.some((term) => term.toLocaleLowerCase() === text.toLocaleLowerCase())
		}));
};

const orderedMatches = (
	result: MailuoObjectResult,
	query: string,
	mode: MailuoSearchMode
): MailuoSnippet[] => {
	if (mode !== 'keyword') return result.matches;
	const ranked = result.matches.map((match, index) => ({
		match,
		index,
		position: literalMatchPosition(normalizeMailuoContent(match.content), query)
	}));
	if (!ranked.some((item) => item.position >= 0)) return result.matches;
	return ranked
		.sort((left, right) => {
			if (left.position < 0 && right.position < 0) return left.index - right.index;
			if (left.position < 0) return 1;
			if (right.position < 0) return -1;
			return left.index - right.index;
		})
		.map((item) => item.match);
};

export const resultsForState = (
	current: MailuoObjectResult[],
	next: MailuoObjectResult[],
	loading: boolean
) => (loading ? current : next);

export const visibleMatches = (
	result: MailuoObjectResult,
	expanded: boolean,
	query = '',
	mode: MailuoSearchMode = 'hybrid'
): MailuoSnippet[] =>
	orderedMatches(result, query, mode)
		.slice(0, expanded ? 3 : 1)
		.map((match) => ({
			...match,
			content: expanded
				? normalizeMailuoContent(match.content)
				: excerptAroundQuery(match.content, query)
		}));

export const sourceLabel = (source: string, labels: Map<string, string>): string =>
	labels.get(source) || source;

export const safeSourceUrl = (value: string): string | null => {
	try {
		const url = new URL(value);
		return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
	} catch {
		return null;
	}
};
