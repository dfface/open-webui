<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	import type { MailuoSearchMode } from '$lib/mailuo/types';

	export let query = '';
	export let mode: MailuoSearchMode = 'hybrid';
	export let loading = false;

	let input: HTMLInputElement;
	const dispatch = createEventDispatcher<{ submit: void }>();

	export const focus = () => input?.focus();

	const modes: { value: MailuoSearchMode; label: string }[] = [
		{ value: 'hybrid', label: '混合' },
		{ value: 'keyword', label: '关键词' },
		{ value: 'semantic', label: '语义' }
	];
</script>

<form
	class="rounded-2xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-gray-900"
	on:submit|preventDefault={() => dispatch('submit')}
>
	<div class="flex items-center gap-2">
		<input
			bind:this={input}
			bind:value={query}
			class="min-w-0 flex-1 bg-transparent px-2 py-2 text-base outline-none placeholder:text-gray-400"
			placeholder="搜索文档、评论、备忘和任务"
			aria-label="搜索脉络"
			autocomplete="off"
		/>
		<button
			type="submit"
			class="rounded-xl bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-gray-900"
			disabled={loading || !query.trim()}
		>
			{loading ? '检索中' : '搜索'}
		</button>
	</div>

	<div class="mt-2 flex flex-wrap gap-1.5 px-1" aria-label="搜索模式">
		{#each modes as item}
			<button
				type="button"
				class="rounded-full px-3 py-1 text-xs transition {mode === item.value
					? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'}"
				aria-pressed={mode === item.value}
				on:click={() => (mode = item.value)}
			>
				{item.label}
			</button>
		{/each}
	</div>
</form>
