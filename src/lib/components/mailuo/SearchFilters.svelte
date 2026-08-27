<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { MailuoKnowledge, MailuoSourceFacet } from '$lib/mailuo/types';

	export let knowledges: MailuoKnowledge[] = [];
	export let facets: MailuoSourceFacet[] = [];
	export let selectedKnowledgeId = '';
	export let selectedSources: string[] = [];

	const dispatch = createEventDispatcher<{ knowledgeChange: void }>();

	const toggleSource = (source: string) => {
		selectedSources = selectedSources.includes(source)
			? selectedSources.filter((item) => item !== source)
			: [...selectedSources, source];
	};
</script>

<section
	class="mt-3 rounded-2xl border border-gray-200/80 bg-gray-50/70 p-3 dark:border-gray-800 dark:bg-gray-900/50"
	aria-labelledby="mailuo-filter-heading"
>
	<div class="mb-2 flex items-center justify-between gap-3">
		<h2 id="mailuo-filter-heading" class="text-xs font-medium text-gray-500 dark:text-gray-400">
			搜索范围
		</h2>
		{#if selectedSources.length > 0}
			<button
				type="button"
				class="min-h-[44px] cursor-pointer rounded-lg px-2 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-200/70 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
				on:click={() => (selectedSources = [])}
			>
				清除来源筛选
			</button>
		{/if}
	</div>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<label class="relative min-w-0 sm:w-56">
			<span class="sr-only">知识库</span>
			<select
				bind:value={selectedKnowledgeId}
				class="min-h-[44px] w-full cursor-pointer appearance-none rounded-xl border border-gray-200 bg-white py-2 pl-3 pr-9 text-sm text-gray-800 outline-none transition-colors hover:border-gray-300 focus:border-gray-400 focus:ring-2 focus:ring-gray-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:hover:border-gray-600 dark:focus:ring-gray-800"
				on:change={() => dispatch('knowledgeChange')}
			>
				<option value="">全部可访问知识库</option>
				{#each knowledges as knowledge}
					<option value={knowledge.id}>{knowledge.name}</option>
				{/each}
			</select>
			<svg
				class="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-gray-400"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				aria-hidden="true"
			>
				<path d="m7 10 5 5 5-5"></path>
			</svg>
		</label>

		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap gap-1.5" aria-label="数据来源">
				{#each facets as facet}
					<button
						type="button"
						class="min-h-[44px] cursor-pointer rounded-xl border px-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-1 dark:focus-visible:ring-offset-gray-900 {selectedSources.includes(
							facet.source
						)
							? 'border-gray-900 bg-gray-900 text-white dark:border-white dark:bg-white dark:text-gray-900'
							: 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:border-gray-600 dark:hover:text-white'}"
						aria-pressed={selectedSources.includes(facet.source)}
						aria-label={`${facet.display_name || facet.source}，${facet.object_count} 个对象`}
						on:click={() => toggleSource(facet.source)}
					>
						{facet.display_name || facet.source}
						<span class="ml-1 tabular-nums opacity-60">{facet.object_count}</span>
					</button>
				{/each}
				{#if facets.length === 0}
					<span class="flex min-h-[44px] items-center text-xs text-gray-400">暂无可用来源</span>
				{/if}
			</div>
		</div>
	</div>
</section>
