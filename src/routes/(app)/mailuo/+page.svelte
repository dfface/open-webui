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
	<main class="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
		<header class="mb-5">
			<div class="text-xs font-medium tracking-[0.18em] text-gray-400">MAILUO</div>
			<h1 class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">脉络</h1>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
				在你有权访问的知识库中进行关键词、语义和混合检索。
			</p>
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

		<section class="mt-5" aria-live="polite">
			<SearchStates
				{initial}
				{loading}
				{error}
				{degraded}
				{warnings}
				empty={!initial && results.length === 0}
			/>

			{#if results.length > 0}
				<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
					找到 {results.length} 个对象
				</div>
				<div class="space-y-3">
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
