<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { safeSourceUrl, visibleMatches } from '$lib/mailuo/view-model';
	import type { MailuoObjectResult } from '$lib/mailuo/types';

	export let result: MailuoObjectResult;
	export let sourceName: string;
	export let expanded = false;

	const dispatch = createEventDispatcher<{ toggle: void }>();

	$: sourceUrl = safeSourceUrl(result.source_url);
	$: matches = visibleMatches(result, expanded);
	$: updatedAt = new Intl.DateTimeFormat('zh-CN', {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	}).format(new Date(result.source_updated_at));

	const channelLabels: Record<string, string> = {
		fulltext: '全文',
		trigram: '关键词',
		semantic: '语义'
	};
</script>

<article
	class="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900"
>
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<h2 class="truncate text-base font-semibold text-gray-900 dark:text-gray-100">
				{result.title || '无标题'}
			</h2>
			<div
				class="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400"
			>
				<span class="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-gray-800">{sourceName}</span>
				{#each result.matched_by as channel}
					<span class="rounded-full border border-gray-200 px-2 py-0.5 dark:border-gray-700">
						{channelLabels[channel] || channel}
					</span>
				{/each}
				<time datetime={result.source_updated_at}>{updatedAt}</time>
			</div>
		</div>

		{#if sourceUrl}
			<a
				href={sourceUrl}
				target="_blank"
				rel="noopener noreferrer"
				class="shrink-0 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
			>
				打开原文
			</a>
		{/if}
	</div>

	<div class="mt-3 space-y-2">
		{#each matches as match}
			<p class="whitespace-pre-wrap text-sm leading-6 text-gray-700 dark:text-gray-300">
				{match.content}
			</p>
		{/each}
	</div>

	{#if result.matches.length > 1}
		<button
			type="button"
			class="mt-2 text-xs font-medium text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
			on:click={() => dispatch('toggle')}
		>
			{expanded ? '收起其他片段' : `再看 ${Math.min(result.matches.length, 3) - 1} 个匹配片段`}
		</button>
	{/if}
</article>
