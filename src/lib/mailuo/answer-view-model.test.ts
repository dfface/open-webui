import { describe, expect, test } from 'vitest';

describe('Mailuo answer view model', () => {
	test('keeps the saved accessible model and falls back to the first accessible model', async () => {
		const module = await import('./answer-view-model').catch(() => null);
		expect(module).not.toBeNull();
		if (!module) return;

		const models = [
			{ id: 'hidden', name: 'Hidden', info: { meta: { hidden: true } } },
			{ id: 'qwen3', name: 'Qwen 3', info: { meta: {} } },
			{ id: 'gpt', name: 'GPT', info: { meta: {} } }
		];

		expect(module.availableAnswerModels(models).map((model) => model.id)).toEqual(['qwen3', 'gpt']);
		expect(module.resolveAnswerModelId(models, 'gpt', ['qwen3'], 'qwen3')).toBe('gpt');
		expect(module.resolveAnswerModelId(models, 'missing', ['qwen3'], 'gpt')).toBe('qwen3');
	});

	test('maps a one-based model citation to the matching evidence result', async () => {
		const module = await import('./answer-view-model').catch(() => null);
		expect(module).not.toBeNull();
		if (!module) return;

		expect(module.citationResultIndex('1', 3)).toBe(0);
		expect(module.citationResultIndex('3#chunk-2', 3)).toBe(2);
		expect(module.citationResultIndex('0', 3)).toBeNull();
		expect(module.citationResultIndex('4', 3)).toBeNull();
	});
});
