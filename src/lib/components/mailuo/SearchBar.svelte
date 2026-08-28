<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { MailuoAnswerModel } from '$lib/mailuo/answer-view-model';
	import type { MailuoIntent, MailuoSearchMode, MailuoSearchSort } from '$lib/mailuo/types';

	export let query = '';
	export let mode: MailuoSearchMode = 'hybrid';
	export let sort: MailuoSearchSort = 'relevance';
	export let intent: MailuoIntent = 'search';
	export let modelId = '';
	export let answerModels: MailuoAnswerModel[] = [];
	export let loading = false;

	let input: HTMLInputElement;
	const dispatch = createEventDispatcher<{ submit: { intent: MailuoIntent } }>();

	export const focus = () => input?.focus();

	const clearQuery = () => {
		query = '';
		input?.focus();
	};

	const modes: { value: MailuoSearchMode; label: string; description: string }[] = [
		{ value: 'hybrid', label: '混合', description: '兼顾原词与语义' },
		{ value: 'keyword', label: '关键词', description: '查找准确表述' },
		{ value: 'semantic', label: '语义', description: '查找相近含义' }
	];

	const submit = (nextIntent: MailuoIntent = intent) => {
		intent = nextIntent;
		dispatch('submit', { intent: nextIntent });
	};
</script>

<form
	class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition-shadow focus-within:border-gray-300 focus-within:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:focus-within:border-gray-700"
	on:submit|preventDefault={() => submit()}
>
	<label for="mailuo-search" class="sr-only">搜索脉络</label>
	<div class="flex items-center gap-2 p-2">
		<svg
			class="ml-2 size-5 shrink-0 text-gray-400"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.8"
			aria-hidden="true"
		>
			<circle cx="11" cy="11" r="7"></circle>
			<path d="m20 20-3.5-3.5"></path>
		</svg>
		<input
			id="mailuo-search"
			bind:this={input}
			bind:value={query}
			class="h-11 min-w-0 flex-1 bg-transparent px-1 text-base text-gray-900 outline-none placeholder:text-gray-400 dark:text-gray-100"
			placeholder="搜索文档、评论、备忘和任务"
			autocomplete="off"
		/>
		{#if query}
			<button
				type="button"
				class="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 dark:hover:bg-gray-800 dark:hover:text-gray-200 dark:focus-visible:ring-offset-gray-900"
				aria-label="清空搜索内容"
				on:click={clearQuery}
			>
				<svg
					class="size-4"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					aria-hidden="true"
				>
					<path d="M18 6 6 18M6 6l12 12"></path>
				</svg>
			</button>
		{/if}
		<button
			type="submit"
			class="flex h-11 min-w-[4.75rem] shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-xl bg-gray-900 px-4 text-sm font-medium text-white transition-colors hover:bg-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200 dark:focus-visible:ring-offset-gray-900"
			disabled={loading || !query.trim() || (intent === 'answer' && !modelId)}
		>
			{#if loading}
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
			{/if}
			<span>{intent === 'answer' ? '问答' : '搜索'}</span>
		</button>
	</div>

	<div
		class="flex flex-wrap items-center gap-2 border-t border-gray-100 px-3 py-2 dark:border-gray-800"
	>
		<span class="px-1 text-xs font-medium text-gray-500 dark:text-gray-400">检索方式</span>
		<div class="flex flex-wrap gap-1" role="group" aria-label="检索方式">
			{#each modes as item}
				<button
					type="button"
					class="min-h-[44px] cursor-pointer rounded-lg px-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-1 dark:focus-visible:ring-offset-gray-900 {mode ===
					item.value
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
						: 'text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'}"
					aria-pressed={mode === item.value}
					aria-label={`${item.label}检索：${item.description}`}
					title={item.description}
					on:click={() => (mode = item.value)}
				>
					{item.label}
				</button>
			{/each}
		</div>
		{#if mode === 'keyword'}
			<label class="flex min-h-[44px] items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
				<span>排序</span>
				<select
					bind:value={sort}
					class="cursor-pointer rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-400 focus:ring-2 focus:ring-gray-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:focus:ring-gray-800"
					aria-label="关键词结果排序"
					disabled={loading}
				>
					<option value="relevance">相关度</option>
					<option value="updated_desc">最近更新</option>
					<option value="updated_asc">最早更新</option>
				</select>
			</label>
		{/if}
		<span class="ml-auto px-1 text-xs font-medium text-gray-500 dark:text-gray-400">用途</span>
		<div
			class="flex h-9 shrink-0 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700"
			role="group"
			aria-label="用途"
		>
			{#each [{ value: 'search', label: '搜索' }, { value: 'answer', label: '问答' }] as action}
				<button
					type="button"
					class="min-w-[3.5rem] cursor-pointer px-3 text-xs font-medium transition-colors focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gray-500 {intent ===
					action.value
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
						: 'bg-white text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100'}"
					disabled={loading}
					aria-pressed={intent === action.value}
					on:click={() => (intent = action.value as MailuoIntent)}
				>
					{action.label}
				</button>
			{/each}
		</div>
		{#if intent === 'answer'}
			<label
				class="flex min-h-[44px] min-w-0 items-center gap-2 text-xs text-gray-500 dark:text-gray-400"
			>
				<span class="hidden sm:inline">问答模型</span>
				<select
					bind:value={modelId}
					class="max-w-44 cursor-pointer rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-400 focus:ring-2 focus:ring-gray-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:focus:ring-gray-800"
					aria-label="问答模型"
					disabled={answerModels.length === 0 || loading}
				>
					{#if answerModels.length === 0}<option value="">暂无可用模型</option>{/if}
					{#each answerModels as model}
						<option value={model.id}>{model.name || model.id}</option>
					{/each}
				</select>
			</label>
		{/if}
	</div>
</form>
