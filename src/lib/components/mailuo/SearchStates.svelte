<script lang="ts">
	export let initial = true;
	export let loading = false;
	export let error = '';
	export let degraded = false;
	export let warnings: string[] = [];
	export let empty = false;
</script>

{#if loading}
	<div
		class="mb-3 rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"
	>
		正在检索，当前结果会保留到新结果返回。
	</div>
{/if}

{#if degraded}
	<div
		class="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
	>
		语义服务暂时不可用，本次已使用关键词检索。
	</div>
{/if}

{#each warnings as warning}
	<div
		class="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
	>
		{warning}
	</div>
{/each}

{#if error}
	<div
		class="rounded-xl bg-red-50 px-3 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300"
	>
		{error}
	</div>
{:else if initial}
	<div class="py-16 text-center text-sm text-gray-500 dark:text-gray-400">
		输入问题或关键词，搜索你有权访问的全部知识来源。
	</div>
{:else if empty && !loading}
	<div class="py-16 text-center text-sm text-gray-500 dark:text-gray-400">
		没有找到结果。可以切换检索模式，或放宽知识库和来源筛选。
	</div>
{/if}
