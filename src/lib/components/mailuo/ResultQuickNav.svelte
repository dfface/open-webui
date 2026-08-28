<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { MailuoObjectResult } from '$lib/mailuo/types';

	export let results: MailuoObjectResult[] = [];
	export let activeIndex = 0;
	export let sourceLabels = new Map<string, string>();

	const dispatch = createEventDispatcher<{ select: { index: number } }>();

	let navElement: HTMLElement;
	let previewIndex: number | null = null;
	let previewTop = 0;

	const showPreview = (index: number, target: HTMLButtonElement) => {
		const navRect = navElement.getBoundingClientRect();
		const targetRect = target.getBoundingClientRect();
		const requestedTop = targetRect.top + targetRect.height / 2 - navRect.top;
		previewTop = Math.min(Math.max(requestedTop, 76), navRect.height - 76);
		previewIndex = index;
	};

	const hidePreview = (index: number) => {
		if (previewIndex === index) previewIndex = null;
	};

	const previewText = (result: MailuoObjectResult) =>
		(result.matches[0]?.content || '').replace(/\s+/g, ' ').trim().slice(0, 180);
</script>

{#if results.length > 2}
	<nav
		bind:this={navElement}
		class="fixed right-4 top-1/2 z-20 hidden max-h-[70vh] -translate-y-1/2 flex-col items-center rounded-2xl border border-gray-200/80 bg-white/90 px-1.5 py-2 shadow-sm backdrop-blur xl:flex dark:border-gray-800 dark:bg-gray-900/90"
		aria-label="搜索结果快速定位"
	>
		{#if previewIndex !== null && results[previewIndex]}
			{@const previewResult = results[previewIndex]}
			<div
				class="pointer-events-none absolute right-full z-30 mr-3 w-72 -translate-y-1/2 rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-xl dark:border-gray-700 dark:bg-gray-900"
				style={`top: ${previewTop}px`}
				aria-hidden="true"
			>
				<div class="mb-1.5 flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
					<span class="font-medium text-gray-700 dark:text-gray-300">
						{sourceLabels.get(previewResult.source) || previewResult.source}
					</span>
					<span aria-hidden="true" class="text-gray-300 dark:text-gray-700">·</span>
					<span>第 {previewIndex + 1} 条</span>
				</div>
				<div class="line-clamp-2 text-sm font-semibold leading-5 text-gray-900 dark:text-gray-100">
					{previewResult.title || '无标题'}
				</div>
				{#if previewText(previewResult)}
					<p class="mt-2 line-clamp-3 text-xs leading-5 text-gray-500 dark:text-gray-400">
						{previewText(previewResult)}
					</p>
				{/if}
			</div>
		{/if}

		<div class="max-h-[60vh] overflow-y-auto overscroll-contain py-0.5">
			{#each results as result, index (`${result.source}:${result.source_object_id}`)}
				<button
					type="button"
					class="group flex h-7 w-11 cursor-pointer items-center justify-end rounded-md px-1 outline-none transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-500 dark:hover:bg-gray-800"
					aria-label={`跳转到第 ${index + 1} 条结果：${result.title || '无标题'}`}
					aria-current={index === activeIndex ? 'true' : undefined}
					title={`${index + 1}. ${result.title || '无标题'}`}
					on:mouseenter={(event) => showPreview(index, event.currentTarget)}
					on:mouseleave={() => hidePreview(index)}
					on:focus={(event) => showPreview(index, event.currentTarget)}
					on:blur={() => hidePreview(index)}
					on:click={() => dispatch('select', { index })}
				>
					<span
						aria-hidden="true"
						class="h-0.5 rounded-full transition-all motion-reduce:transition-none {index ===
						activeIndex
							? 'w-9 bg-gray-900 dark:bg-gray-100'
							: 'w-5 bg-gray-300 group-hover:w-8 group-hover:bg-gray-500 dark:bg-gray-700 dark:group-hover:bg-gray-500'}"
					></span>
				</button>
			{/each}
		</div>
		<div
			class="mt-1 border-t border-gray-100 px-1 pt-1.5 text-[10px] tabular-nums text-gray-400 dark:border-gray-800 dark:text-gray-500"
			aria-hidden="true"
		>
			{Math.min(activeIndex + 1, results.length)}/{results.length}
		</div>
	</nav>
{/if}
