<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import { highlightMailuoText, safeSourceUrl, visibleMatches } from '$lib/mailuo/view-model';
	import type { MailuoObjectResult, MailuoSearchMode } from '$lib/mailuo/types';

	export let result: MailuoObjectResult;
	export let sourceName: string;
	export let query = '';
	export let mode: MailuoSearchMode = 'hybrid';
	export let expanded = false;

	const dispatch = createEventDispatcher<{ toggle: void }>();

	$: sourceUrl = safeSourceUrl(result.source_url);
	$: matches = visibleMatches(result, expanded, query, mode);

	const formatDate = (value: string) => {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return '';
		return new Intl.DateTimeFormat('zh-CN', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		}).format(date);
	};

	$: updatedAt = formatDate(result.source_updated_at);

	const channelLabels: Record<string, string> = {
		fulltext: '全文',
		trigram: '关键词',
		semantic: '语义'
	};
</script>

<article class="group p-4 transition-colors hover:bg-gray-50/70 dark:hover:bg-gray-800/30 sm:p-5">
	<div class="flex items-start gap-3">
		<div class="min-w-0 flex-1">
			<h2 class="line-clamp-2 text-base font-semibold leading-6 text-gray-900 dark:text-gray-100">
				{#if sourceUrl}
					<a
						href={sourceUrl}
						target="_blank"
						rel="noopener noreferrer"
						class="rounded-sm outline-none transition-colors hover:text-gray-600 hover:underline focus-visible:ring-2 focus-visible:ring-gray-500 dark:hover:text-white"
					>
						{#each highlightMailuoText(result.title || '无标题', query) as segment}
							{#if segment.highlighted}
								<mark class="rounded-sm bg-amber-200 px-0.5 text-inherit dark:bg-amber-500/35"
									>{segment.text}</mark
								>
							{:else}{segment.text}{/if}
						{/each}
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
				class="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 dark:text-gray-500 dark:hover:bg-gray-800 dark:hover:text-gray-100 dark:focus-visible:ring-offset-gray-900"
				aria-label={`打开原文：${result.title || '无标题'}`}
				title="打开原文"
			>
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

	<div class="mt-3 max-w-3xl space-y-3">
		{#each matches as match, index}
			<div class={index > 0 ? 'border-t border-gray-100 pt-3 dark:border-gray-800' : ''}>
				<p
					class="whitespace-pre-wrap break-words text-sm leading-6 text-gray-700 dark:text-gray-300"
				>
					{#each highlightMailuoText(match.content, query) as segment}
						{#if segment.highlighted}
							<mark class="rounded-sm bg-amber-200 px-0.5 text-inherit dark:bg-amber-500/35"
								>{segment.text}</mark
							>
						{:else}{segment.text}{/if}
					{/each}
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
