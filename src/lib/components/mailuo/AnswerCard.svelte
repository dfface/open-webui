<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import type { MailuoObjectResult } from '$lib/mailuo/types';
	import { citationResultIndex } from '$lib/mailuo/answer-view-model';

	export let content = '';
	export let loading = false;
	export let error = '';
	export let modelName = '';
	export let results: MailuoObjectResult[] = [];

	const dispatch = createEventDispatcher<{
		stop: void;
		retry: void;
		citation: { index: number };
	}>();

	$: sourceTitles = results.map((result) => result.title || result.source);

	const openCitation = (citationId: string | number) => {
		const index = citationResultIndex(citationId, results.length);
		if (index !== null) dispatch('citation', { index });
	};
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

	<div class="px-4 py-4 sm:px-5 sm:py-5">
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
					id="mailuo-answer"
					messageId="mailuo-answer"
					{content}
					done={!loading}
					save={false}
					editCodeBlock={false}
					allowEmbeds={false}
					sourceIds={sourceTitles}
					onSourceClick={openCitation}
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
	</div>
</article>
