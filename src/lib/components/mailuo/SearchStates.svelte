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
		class="mb-3 flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2.5 text-sm text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"
		role="status"
	>
		<svg
			class="size-4 shrink-0 animate-spin motion-reduce:animate-none"
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
		正在检索，当前结果会保留到新结果返回。
	</div>
{/if}

{#if degraded}
	<div
		class="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
		role="status"
	>
		语义服务暂时不可用，本次已使用关键词检索。
	</div>
{/if}

{#each warnings as warning}
	<div
		class="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
		role="status"
	>
		{warning}
	</div>
{/each}

{#if error}
	<div
		class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
		role="alert"
	>
		<div class="font-medium">搜索暂时不可用</div>
		<div class="mt-1">{error}。请稍后重试。</div>
	</div>
{:else if initial}
	<div
		class="rounded-2xl border border-dashed border-gray-200 px-6 py-12 text-center dark:border-gray-800"
	>
		<svg
			class="mx-auto size-6 text-gray-400"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.7"
			aria-hidden="true"
		>
			<circle cx="11" cy="11" r="7"></circle>
			<path d="m20 20-3.5-3.5"></path>
		</svg>
		<div class="mt-3 text-sm font-medium text-gray-700 dark:text-gray-200">
			从一个问题或概念开始
		</div>
		<p class="mx-auto mt-1 max-w-md text-sm leading-6 text-gray-500 dark:text-gray-400">
			脉络会在你有权访问的知识来源中查找相关内容，并带你回到原文。
		</p>
	</div>
{:else if empty && !loading}
	<div
		class="rounded-2xl border border-dashed border-gray-200 px-6 py-12 text-center dark:border-gray-800"
	>
		<div class="text-sm font-medium text-gray-700 dark:text-gray-200">没有找到匹配内容</div>
		<p class="mt-1 text-sm leading-6 text-gray-500 dark:text-gray-400">
			试试更短的关键词、切换检索方式，或清除部分范围筛选。
		</p>
	</div>
{/if}
