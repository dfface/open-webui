import type { MailuoObjectResult, MailuoSnippet } from './types';

export const resultsForState = (
	current: MailuoObjectResult[],
	next: MailuoObjectResult[],
	loading: boolean
) => (loading ? current : next);

export const visibleMatches = (result: MailuoObjectResult, expanded: boolean): MailuoSnippet[] =>
	result.matches.slice(0, expanded ? 3 : 1);

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
