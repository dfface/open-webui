<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import SearchBar from '$lib/components/mailuo/SearchBar.svelte';
	import SearchFilters from '$lib/components/mailuo/SearchFilters.svelte';
	import SearchResult from '$lib/components/mailuo/SearchResult.svelte';
	import SearchStates from '$lib/components/mailuo/SearchStates.svelte';
	import { getMailuoFacets, getMailuoKnowledges, searchMailuo } from '$lib/mailuo/api';
	import { parseMailuoQueryState, serializeMailuoQueryState } from '$lib/mailuo/query-state';
	import type {
		MailuoKnowledge,
		MailuoObjectResult,
		MailuoSearchMode,
		MailuoSourceFacet
	} from '$lib/mailuo/types';
	import { resultsForState, sourceLabel } from '$lib/mailuo/view-model';

	let searchBar: SearchBar;
	let query = '';
	let mode: MailuoSearchMode = 'hybrid';
	let selectedKnowledgeId = '';
	let selectedSources: string[] = [];

	let knowledges: MailuoKnowledge[] = [];
	let facets: MailuoSourceFacet[] = [];
	let results: MailuoObjectResult[] = [];
	let loading = false;
	let initial = true;
	let error = '';
	let degraded = false;
	let warnings: string[] = [];
	let expandedResults = new Set<string>();

	$: sourceLabels = new Map(facets.map((facet) => [facet.source, facet.display_name]));

	const knowledgeIds = () => (selectedKnowledgeId ? [selectedKnowledgeId] : undefined);

	const loadFacets = async () => {
		const response = await getMailuoFacets(localStorage.token, knowledgeIds());
		facets = response.sources;
		const available = new Set(facets.map((facet) => facet.source));
		selectedSources = selectedSources.filter((source) => available.has(source));
	};

	const syncUrl = () => {
		const search = serializeMailuoQueryState({
			query,
			mode,
			knowledgeIds: selectedKnowledgeId ? [selectedKnowledgeId] : [],
			sources: selectedSources
		});
		window.history.pushState({}, '', `/mailuo${search ? `?${search}` : ''}`);
	};

	const executeSearch = async (updateUrl = true) => {
		query = query.trim();
		if (!query || loading) return;
		loading = true;
		error = '';
		if (updateUrl) syncUrl();

		try {
			const response = await searchMailuo(localStorage.token, {
				query,
				mode,
				knowledge_ids: knowledgeIds(),
				sources: selectedSources.length ? selectedSources : undefined,
				limit: 20
			});
			results = resultsForState(results, response.results, false);
			degraded = response.degraded;
			warnings = response.warnings;
			initial = false;
			expandedResults = new Set();
		} catch (searchError) {
			error = searchError instanceof Error ? searchError.message : '脉络搜索失败';
			degraded = false;
			warnings = [];
			initial = false;
		} finally {
			loading = false;
		}
	};

	const applyUrl = async (url: URL, runSearch: boolean) => {
		const state = parseMailuoQueryState(url);
		query = state.query;
		mode = state.mode;
		selectedKnowledgeId = state.knowledgeIds[0] || '';
		selectedSources = state.sources;
		await loadFacets();
		if (runSearch && query) await executeSearch(false);
	};

	const onPopState = () => applyUrl(new URL(window.location.href), true);

	const onWindowKeydown = (event: KeyboardEvent) => {
		const target = event.target as HTMLElement | null;
		const editing = target?.matches('input, textarea, [contenteditable="true"]');
		if (event.key === '/' && !editing) {
			event.preventDefault();
			searchBar?.focus();
		}
		if (event.key === 'Escape') {
			query = '';
			searchBar?.focus();
		}
	};

	const toggleExpanded = (result: MailuoObjectResult) => {
		const key = `${result.source}:${result.source_object_id}`;
		const next = new Set(expandedResults);
		next.has(key) ? next.delete(key) : next.add(key);
		expandedResults = next;
	};

	onMount(async () => {
		window.addEventListener('popstate', onPopState);
		window.addEventListener('keydown', onWindowKeydown);
		try {
			knowledges = await getMailuoKnowledges(localStorage.token);
			await applyUrl(new URL(window.location.href), true);
		} catch (loadError) {
			error = loadError instanceof Error ? loadError.message : '无法加载脉络知识库';
			initial = false;
		}
	});

	onDestroy(() => {
		window.removeEventListener('popstate', onPopState);
		window.removeEventListener('keydown', onWindowKeydown);
	});
</script>

<svelte:head>
	<title>脉络</title>
</svelte:head>

<div class="h-full overflow-y-auto">
	<main class="mx-auto w-full max-w-5xl px-4 pb-12 pt-6 sm:px-6 sm:pt-8 lg:px-8">
		<header class="mb-6 flex items-start justify-between gap-6">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">脉络</h1>
				<p class="mt-1.5 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
					搜索分散在不同系统里的文档、评论、备忘和任务。
				</p>
			</div>
			<div
				class="hidden items-center gap-1.5 pt-1 text-xs text-gray-400 md:flex"
				aria-hidden="true"
			>
				<kbd
					class="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 font-sans dark:border-gray-800 dark:bg-gray-900"
					>/</kbd
				>
				<span>聚焦搜索</span>
			</div>
		</header>

		<SearchBar
			bind:this={searchBar}
			bind:query
			bind:mode
			{loading}
			on:submit={() => executeSearch()}
		/>
		<SearchFilters
			{knowledges}
			{facets}
			bind:selectedKnowledgeId
			bind:selectedSources
			on:knowledgeChange={loadFacets}
		/>

		<section class="mt-6" aria-label="搜索结果" aria-busy={loading}>
			<SearchStates
				{initial}
				{loading}
				{error}
				{degraded}
				{warnings}
				empty={!initial && results.length === 0}
			/>

			{#if results.length > 0}
				<div class="mb-3 flex items-center justify-between gap-3 px-1">
					<h2
						id="mailuo-results-heading"
						class="text-sm font-medium text-gray-700 dark:text-gray-200"
					>
						{results.length} 条结果
					</h2>
					<div class="text-xs text-gray-400" aria-live="polite">
						{mode === 'hybrid' ? '混合检索' : mode === 'keyword' ? '关键词检索' : '语义检索'}
					</div>
				</div>
				<div
					class="space-y-3 transition-opacity duration-200 motion-reduce:transition-none {loading
						? 'opacity-60'
						: ''}"
				>
					{#each results as result (result.source + ':' + result.source_object_id)}
						<SearchResult
							{result}
							sourceName={sourceLabel(result.source, sourceLabels)}
							expanded={expandedResults.has(`${result.source}:${result.source_object_id}`)}
							on:toggle={() => toggleExpanded(result)}
						/>
					{/each}
				</div>
			{/if}
		</section>
	</main>
</div>
