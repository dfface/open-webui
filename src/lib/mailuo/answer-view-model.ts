import type { MailuoAnswerTurn, MailuoConversationMessage } from './types';

export type MailuoAnswerModel = {
	id: string;
	name?: string;
	info?: { meta?: { hidden?: boolean } };
};

export const availableAnswerModels = <T extends MailuoAnswerModel>(models: T[]): T[] =>
	models.filter((model) => Boolean(model.id) && model.info?.meta?.hidden !== true);

export const resolveAnswerModelId = (
	models: MailuoAnswerModel[],
	savedModelId: string,
	preferredModelIds: string[] = [],
	defaultModelId = ''
): string => {
	const available = availableAnswerModels(models);
	const ids = new Set(available.map((model) => model.id));
	return (
		[savedModelId, ...preferredModelIds, defaultModelId].find((modelId) => ids.has(modelId)) ??
		available[0]?.id ??
		''
	);
};

export const citationResultIndex = (
	citationId: string | number,
	resultCount: number
): number | null => {
	const number = Number.parseInt(String(citationId).split('#', 1)[0], 10);
	return Number.isInteger(number) && number >= 1 && number <= resultCount ? number - 1 : null;
};

export const answerHistoryFromTurns = (
	turns: MailuoAnswerTurn[],
	maxMessages = 8
): MailuoConversationMessage[] =>
	turns
		.flatMap<MailuoConversationMessage>((turn) => [
			{ role: 'user', content: turn.question },
			{ role: 'assistant', content: turn.content }
		])
		.slice(-maxMessages);
