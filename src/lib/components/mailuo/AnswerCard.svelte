<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import type { MailuoAnswerTurn, MailuoObjectResult, MailuoSearchMode } from '$lib/mailuo/types';
	import { citationResultIndex } from '$lib/mailuo/answer-view-model';

	export let question = '';
	export let content = '';
	export let loading = false;
	export let error = '';
	export let modelName = '';
	export let results: MailuoObjectResult[] = [];
	export let resultMode: MailuoSearchMode = 'hybrid';
	export let previousTurns: MailuoAnswerTurn[] = [];

	let followUp = '';

	const dispatch = createEventDispatcher<{
		stop: void;
		retry: void;
		followup: { query: string };
		citation: {
			index: number;
			results: MailuoObjectResult[];
			query: string;
			mode: MailuoSearchMode;
		};
	}>();

	$: sourceTitles = results.map((result) => result.title || result.source);

	const openCitation = (
		citationId: string | number,
		evidence: MailuoObjectResult[],
		evidenceQuery: string,
		evidenceMode: MailuoSearchMode
	) => {
		const index = citationResultIndex(citationId, evidence.length);
		if (index !== null) {
			dispatch('citation', {
				index,
				results: evidence,
				query: evidenceQuery,
				mode: evidenceMode
			});
		}
	};

	const submitFollowUp = () => {
		const nextQuery = followUp.trim();
		if (!nextQuery || loading) return;
		followUp = '';
		dispatch('followup', { query: nextQuery });
	};

	const citationHandler = (
		evidence: MailuoObjectResult[],
		evidenceQuery: string,
		evidenceMode: MailuoSearchMode
	) =>
		((citationId: string | number) =>
			openCitation(citationId, evidence, evidenceQuery, evidenceMode)) as () => void;
</script>

<article
	class="mb-5 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
	aria-labelledby="mailuo-answer-heading"
>
	<header
		class="flex min-h-[52px] items-center justify-between gap-3 border-b border-gray-100 px-4 dark:border-gray-800 sm:px-5"
	>
		<div class="flex min-w-0 items-center gap-2">
			<h2 id="mailuo-answer-heading" class="text-sm font-semibold text-gray-900 dark:text-gray-100">
				回答
			</h2>
			{#if modelName}
				<span class="truncate text-xs text-gray-500 dark:text-gray-400">{modelName}</span>
			{/if}
		</div>
		{#if loading}
			<button
				type="button"
				class="min-h-[44px] rounded-lg px-3 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
				on:click={() => dispatch('stop')}
			>
				停止生成
			</button>
		{:else if content || error}
			<button
				type="button"
				class="min-h-[44px] rounded-lg px-3 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
				on:click={() => dispatch('retry')}
			>
				重新生成
			</button>
		{/if}
	</header>

	<div class="divide-y divide-gray-100 dark:divide-gray-800">
		{#each previousTurns as turn, index}
			<section class="px-4 py-4 sm:px-5 sm:py-5" aria-label={`第 ${index + 1} 轮问答`}>
				<div
					class="mb-4 ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-md bg-gray-100 px-3.5 py-2 text-sm leading-6 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
				>
					{turn.question}
				</div>
				<div class="markdown-prose text-sm leading-7 text-gray-800 dark:text-gray-200">
					<Markdown
						id={`mailuo-answer-${index}`}
						messageId={`mailuo-answer-${index}`}
						content={turn.content}
						done={true}
						save={false}
						editCodeBlock={false}
						allowEmbeds={false}
						sourceIds={turn.results.map((result) => result.title || result.source)}
						onSourceClick={citationHandler(turn.results, turn.question, turn.mode)}
					/>
				</div>
			</section>
		{/each}

		<section class="px-4 py-4 sm:px-5 sm:py-5" aria-label="当前问答">
			{#if question}
				<div
					class="mb-4 ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-md bg-gray-100 px-3.5 py-2 text-sm leading-6 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
				>
					{question}
				</div>
			{/if}

			{#if error}
				<div
					class="rounded-xl bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300"
					role="alert"
				>
					{error}
				</div>
			{:else if content}
				<div
					class="markdown-prose text-sm leading-7 text-gray-800 dark:text-gray-200"
					aria-live="polite"
				>
					<Markdown
						id="mailuo-answer-current"
						messageId="mailuo-answer-current"
						{content}
						done={!loading}
						save={false}
						editCodeBlock={false}
						allowEmbeds={false}
						sourceIds={sourceTitles}
						onSourceClick={citationHandler(results, question, resultMode)}
					/>
				</div>
			{:else}
				<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400" role="status">
					<svg
						class="size-4 animate-spin motion-reduce:animate-none"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="9"
							fill="none"
							stroke="currentColor"
							stroke-width="3"
						></circle>
						<path class="opacity-80" fill="currentColor" d="M21 12a9 9 0 0 0-9-9v3a6 6 0 0 1 6 6h3Z"
						></path>
					</svg>
					<span>正在检索证据并组织回答…</span>
				</div>
			{/if}
		</section>
	</div>

	{#if !loading && content && !error}
		<form
			class="flex items-center gap-2 border-t border-gray-100 p-3 dark:border-gray-800 sm:px-4"
			on:submit|preventDefault={submitFollowUp}
		>
			<label for="mailuo-follow-up" class="sr-only">继续追问</label>
			<input
				id="mailuo-follow-up"
				bind:value={followUp}
				class="h-11 min-w-0 flex-1 rounded-xl border border-gray-200 bg-transparent px-3 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-gray-400 focus:ring-2 focus:ring-gray-200 dark:border-gray-700 dark:text-gray-100 dark:focus:border-gray-600 dark:focus:ring-gray-800"
				placeholder="基于这些内容继续追问…"
				autocomplete="off"
			/>
			<button
				type="submit"
				class="h-11 shrink-0 rounded-xl bg-gray-900 px-4 text-sm font-medium text-white transition-colors hover:bg-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200 dark:focus-visible:ring-offset-gray-900"
				disabled={!followUp.trim()}
			>
				追问
			</button>
		</form>
	{/if}
</article>
