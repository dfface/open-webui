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

	const formatDate = (value: string) => {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return '';
		return new Intl.DateTimeFormat('zh-CN', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		}).format(date);
	};

	const normalizeContent = (content: string) =>
		content
			.replace(/\\r\\n|\\n|\\r/g, '\n')
			.replace(/\n{3,}/g, '\n\n')
			.trim();

	$: updatedAt = formatDate(result.source_updated_at);

	const channelLabels: Record<string, string> = {
		fulltext: '全文',
		trigram: '关键词',
		semantic: '语义'
	};
</script>

<article
	class="group rounded-2xl border border-gray-200 bg-white p-4 transition-colors hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700 sm:p-5"
>
	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0">
			<h2 class="line-clamp-2 text-base font-semibold leading-6 text-gray-900 dark:text-gray-100">
				{#if sourceUrl}
					<a
						href={sourceUrl}
						target="_blank"
						rel="noopener noreferrer"
						class="rounded-sm outline-none transition-colors hover:text-gray-600 hover:underline focus-visible:ring-2 focus-visible:ring-gray-500 dark:hover:text-white"
					>
						{result.title || '无标题'}
					</a>
				{:else}
					{result.title || '无标题'}
				{/if}
			</h2>
			<div
				class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500 dark:text-gray-400"
			>
				<span class="font-medium text-gray-600 dark:text-gray-300">{sourceName}</span>
				<span aria-hidden="true" class="text-gray-300 dark:text-gray-700">·</span>
				{#each result.matched_by as channel}
					<span class="rounded-md bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">
						{channelLabels[channel] || channel}
					</span>
				{/each}
				{#if updatedAt}<time datetime={result.source_updated_at}>{updatedAt}</time>{/if}
			</div>
		</div>

		{#if sourceUrl}
			<a
				href={sourceUrl}
				target="_blank"
				rel="noopener noreferrer"
				class="flex min-h-[44px] shrink-0 cursor-pointer items-center gap-1.5 rounded-xl border border-gray-200 px-3 text-xs font-medium text-gray-700 transition-colors hover:border-gray-300 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 dark:border-gray-700 dark:text-gray-200 dark:hover:border-gray-600 dark:hover:bg-gray-800 dark:focus-visible:ring-offset-gray-900"
				aria-label={`打开原文：${result.title || '无标题'}`}
			>
				<span class="hidden sm:inline">打开原文</span>
				<svg
					class="size-4"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.8"
					aria-hidden="true"
				>
					<path d="M15 5h4v4M14 10l5-5M19 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"
					></path>
				</svg>
			</a>
		{/if}
	</div>

	<div class="mt-4 space-y-3">
		{#each matches as match, index}
			<div class={index > 0 ? 'border-t border-gray-100 pt-3 dark:border-gray-800' : ''}>
				<p
					class="whitespace-pre-wrap break-words text-sm leading-6 text-gray-700 dark:text-gray-300 {expanded
						? ''
						: 'line-clamp-4'}"
				>
					{normalizeContent(match.content)}
				</p>
			</div>
		{/each}
	</div>

	{#if result.matches.length > 1 || result.matches[0]?.content.length > 360}
		<button
			type="button"
			class="mt-3 flex min-h-[44px] cursor-pointer items-center gap-1 rounded-lg pr-2 text-xs font-medium text-gray-500 transition-colors hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 dark:text-gray-400 dark:hover:text-white"
			aria-expanded={expanded}
			on:click={() => dispatch('toggle')}
		>
			<span
				>{expanded
					? '收起内容'
					: result.matches.length > 1
						? `展开匹配内容（${Math.min(result.matches.length, 3)} 个片段）`
						: '展开完整内容'}</span
			>
			<svg
				class="size-4 transition-transform motion-reduce:transition-none {expanded
					? 'rotate-180'
					: ''}"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				aria-hidden="true"
			>
				<path d="m7 10 5 5 5-5"></path>
			</svg>
		</button>
	{/if}
</article>
