<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { MailuoObjectResult } from '$lib/mailuo/types';

	export let results: MailuoObjectResult[] = [];
	export let activeIndex = 0;

	const dispatch = createEventDispatcher<{ select: { index: number } }>();
</script>

{#if results.length > 2}
	<nav
		class="fixed right-4 top-1/2 z-20 hidden max-h-[70vh] -translate-y-1/2 flex-col items-center rounded-2xl border border-gray-200/80 bg-white/90 px-1.5 py-2 shadow-sm backdrop-blur xl:flex dark:border-gray-800 dark:bg-gray-900/90"
		aria-label="搜索结果快速定位"
	>
		<div class="max-h-[60vh] overflow-y-auto overscroll-contain py-0.5">
			{#each results as result, index (`${result.source}:${result.source_object_id}`)}
				<button
					type="button"
					class="group flex h-7 w-11 cursor-pointer items-center justify-end rounded-md px-1 outline-none transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-500 dark:hover:bg-gray-800"
					aria-label={`跳转到第 ${index + 1} 条结果：${result.title || '无标题'}`}
					aria-current={index === activeIndex ? 'true' : undefined}
					title={`${index + 1}. ${result.title || '无标题'}`}
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
