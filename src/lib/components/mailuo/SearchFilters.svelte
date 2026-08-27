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

<div
	class="mt-3 flex flex-col gap-3 rounded-2xl border border-gray-100 bg-gray-50/70 p-3 text-sm dark:border-gray-800 dark:bg-gray-900/50 sm:flex-row sm:items-start"
>
	<label class="flex min-w-48 flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
		知识库
		<select
			bind:value={selectedKnowledgeId}
			class="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-800 outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
			on:change={() => dispatch('knowledgeChange')}
		>
			<option value="">全部可访问知识库</option>
			{#each knowledges as knowledge}
				<option value={knowledge.id}>{knowledge.name}</option>
			{/each}
		</select>
	</label>

	<div class="min-w-0 flex-1">
		<div class="mb-1 text-xs text-gray-500 dark:text-gray-400">数据来源</div>
		<div class="flex flex-wrap gap-1.5">
			{#each facets as facet}
				<button
					type="button"
					class="rounded-full border px-2.5 py-1 text-xs transition {selectedSources.includes(
						facet.source
					)
						? 'border-gray-900 bg-gray-900 text-white dark:border-white dark:bg-white dark:text-gray-900'
						: 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300'}"
					aria-pressed={selectedSources.includes(facet.source)}
					on:click={() => toggleSource(facet.source)}
				>
					{facet.display_name || facet.source}
					<span class="ml-1 opacity-60">{facet.object_count}</span>
				</button>
			{/each}
			{#if facets.length === 0}
				<span class="py-1 text-xs text-gray-400">暂无可用来源</span>
			{/if}
		</div>
	</div>
</div>
