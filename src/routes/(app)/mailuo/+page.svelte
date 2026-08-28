<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';
	import { browser } from '$app/environment';
	import { config, models, settings, showSidebar } from '$lib/stores';

	import AnswerCard from '$lib/components/mailuo/AnswerCard.svelte';
	import SearchBar from '$lib/components/mailuo/SearchBar.svelte';
	import SearchFilters from '$lib/components/mailuo/SearchFilters.svelte';
	import ResultQuickNav from '$lib/components/mailuo/ResultQuickNav.svelte';
	import SearchResult from '$lib/components/mailuo/SearchResult.svelte';
	import SearchStates from '$lib/components/mailuo/SearchStates.svelte';
	import {
		answerMailuo,
		getMailuoFacets,
		getMailuoKnowledges,
		searchMailuo
	} from '$lib/mailuo/api';
	import {
		answerHistoryFromTurns,
		availableAnswerModels,
		resolveAnswerModelId
	} from '$lib/mailuo/answer-view-model';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { parseMailuoQueryState, serializeMailuoQueryState } from '$lib/mailuo/query-state';
	import type {
		MailuoAnswerTurn,
		MailuoKnowledge,
		MailuoIntent,
		MailuoObjectResult,
		MailuoSearchMode,
		MailuoSearchResponse,
		MailuoSearchSort,
		MailuoSourceFacet
	} from '$lib/mailuo/types';
	import { resultsForState, sourceLabel } from '$lib/mailuo/view-model';

	let searchBar: SearchBar;
	let query = '';
	let mode: MailuoSearchMode = 'hybrid';
	let sort: MailuoSearchSort = 'relevance';
	let intent: MailuoIntent = 'search';
	let selectedModelId = '';
	let selectedKnowledgeId = '';
	let selectedSources: string[] = [];

	let knowledges: MailuoKnowledge[] = [];
	let facets: MailuoSourceFacet[] = [];
	let results: MailuoObjectResult[] = [];
	let resultQuery = '';
	let resultMode: MailuoSearchMode = 'hybrid';
	let searchLoading = false;
	let answerLoading = false;
	let initial = true;
	let error = '';
	let degraded = false;
	let warnings: string[] = [];
	let answer = '';
	let answerError = '';
	let answerQuestion = '';
	let answerResults: MailuoObjectResult[] = [];
	let answerResultMode: MailuoSearchMode = 'hybrid';
	let answerTurns: MailuoAnswerTurn[] = [];
	let answerController: AbortController | undefined;
	let expandedResults = new Set<string>();
	let resultViewport: HTMLDivElement;
	let activeResultIndex = 0;
	let scrollFrame: number | undefined;

	$: sourceLabels = new Map(facets.map((facet) => [facet.source, facet.display_name]));
	$: answerModels = availableAnswerModels($models);
	$: selectedModel = answerModels.find((model) => model.id === selectedModelId);
	$: loading = searchLoading || answerLoading;
	$: if (answerModels.length > 0 && !answerModels.some((model) => model.id === selectedModelId)) {
		selectedModelId = resolveAnswerModelId(
			answerModels,
			browser ? (localStorage.getItem('mailuo_answer_model') ?? '') : '',
			$settings?.models ?? [],
			($config?.default_models ?? '').split(',').find(Boolean) ?? ''
		);
	}
	$: if (browser && selectedModelId) localStorage.setItem('mailuo_answer_model', selectedModelId);

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
			sort,
			knowledgeIds: selectedKnowledgeId ? [selectedKnowledgeId] : [],
			sources: selectedSources
		});
		window.history.pushState({}, '', `/mailuo${search ? `?${search}` : ''}`);
	};

	const executeSearch = async (updateUrl = true) => {
		query = query.trim();
		if (!query || loading) return;
		searchLoading = true;
		error = '';
		answer = '';
		answerError = '';
		answerQuestion = '';
		answerResults = [];
		answerResultMode = 'hybrid';
		answerTurns = [];
		if (updateUrl) syncUrl();

		try {
			const response = await searchMailuo(localStorage.token, {
				query,
				mode,
				knowledge_ids: knowledgeIds(),
				sources: selectedSources.length ? selectedSources : undefined,
				limit: mode === 'keyword' ? 150 : 20,
				sort: mode === 'keyword' ? sort : 'relevance'
			});
			results = resultsForState(results, response.results, false);
			resultQuery = query;
			resultMode = response.executed_mode;
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
			searchLoading = false;
		}
	};

	const executeAnswer = async (
		updateUrl = true,
		question = query,
		conversationMode: 'new' | 'followup' | 'retry' = 'new'
	) => {
		question = question.trim();
		if (!question || loading || !selectedModelId) return;

		let historyTurns: MailuoAnswerTurn[] = conversationMode === 'new' ? [] : answerTurns;
		if (conversationMode === 'followup' && answerQuestion && answer) {
			historyTurns = [
				...historyTurns,
				{
					question: answerQuestion,
					content: answer,
					results: answerResults,
					mode: answerResultMode
				}
			].slice(-4);
		}
		answerTurns = historyTurns;
		answerQuestion = question;
		query = question;
		answerController?.abort();
		answerLoading = true;
		answer = '';
		answerError = '';
		answerResults = [];
		answerResultMode = mode;
		results = [];
		error = '';
		initial = false;
		if (updateUrl) syncUrl();

		try {
			const [response, controller] = await answerMailuo(localStorage.token, {
				query,
				model: selectedModelId,
				mode,
				knowledge_ids: knowledgeIds(),
				sources: selectedSources.length ? selectedSources : undefined,
				sort: mode === 'keyword' ? sort : 'relevance',
				history: answerHistoryFromTurns(historyTurns)
			});
			answerController = controller;
			if (!response.body) throw new Error('模型没有返回可读取的回答');
			const stream = await createOpenAITextStream(response.body, false);
			for await (const update of stream) {
				if (update.error) throw new Error(update.error?.message ?? '模型回答失败');
				if (update.sources) {
					const evidence = update.sources as MailuoSearchResponse;
					answerResults = evidence.results;
					answerResultMode = evidence.executed_mode;
					results = evidence.results;
					resultQuery = answerQuestion;
					resultMode = evidence.executed_mode;
					degraded = evidence.degraded;
					warnings = evidence.warnings;
					expandedResults = new Set();
				}
				if (update.value) answer += update.value;
				if (update.done) break;
			}
		} catch (answerFailure) {
			if ((answerFailure as DOMException)?.name !== 'AbortError') {
				answerError = answerFailure instanceof Error ? answerFailure.message : '脉络问答失败';
			}
		} finally {
			answerLoading = false;
			answerController = undefined;
		}
	};

	const execute = (nextIntent: MailuoIntent, updateUrl = true) => {
		intent = nextIntent;
		return nextIntent === 'answer'
			? executeAnswer(updateUrl, query, 'new')
			: executeSearch(updateUrl);
	};

	const applyUrl = async (url: URL, runSearch: boolean) => {
		const state = parseMailuoQueryState(url);
		query = state.query;
		mode = state.mode;
		sort = state.sort;
		selectedKnowledgeId = state.knowledgeIds[0] || '';
		selectedSources = state.sources;
		await loadFacets();
		if (runSearch && query) await executeSearch(false);
	};

	const onPopState = () => applyUrl(new URL(window.location.href), true);

	const resultKey = (result: MailuoObjectResult) => `${result.source}:${result.source_object_id}`;

	const resultElements = () =>
		Array.from(resultViewport?.querySelectorAll<HTMLElement>('[data-mailuo-result-index]') ?? []);

	const updateActiveResult = () => {
		const elements = resultElements();
		if (!resultViewport || elements.length === 0) return;

		const viewportTop = resultViewport.getBoundingClientRect().top + 112;
		let nextIndex = 0;
		for (const [index, element] of elements.entries()) {
			if (element.getBoundingClientRect().top <= viewportTop) nextIndex = index;
			else break;
		}
		activeResultIndex = nextIndex;
	};

	const onResultsScroll = () => {
		if (scrollFrame !== undefined) return;
		scrollFrame = window.requestAnimationFrame(() => {
			scrollFrame = undefined;
			updateActiveResult();
		});
	};

	const jumpToResult = (index: number, behavior: ScrollBehavior = 'smooth') => {
		const target = resultElements()[index];
		if (!target) return;
		const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		target.scrollIntoView({ behavior: reducedMotion ? 'auto' : behavior, block: 'start' });
		target.focus({ preventScroll: true });
		activeResultIndex = index;
	};

	const showAnswerCitation = async (detail: {
		index: number;
		results: MailuoObjectResult[];
		query: string;
		mode: MailuoSearchMode;
	}) => {
		results = detail.results;
		resultQuery = detail.query;
		resultMode = detail.mode;
		await tick();
		jumpToResult(detail.index);
	};

	const onWindowKeydown = (event: KeyboardEvent) => {
		const target = event.target as HTMLElement | null;
		const editing = target?.matches('input, textarea, [contenteditable="true"]');
		if (event.key === '/' && !editing) {
			event.preventDefault();
			searchBar?.focus();
		}
		if (event.key === 'Escape') {
			if (expandedResults.size > 0) {
				event.preventDefault();
				const expandedIndex = results.findIndex(
					(result, index) => index >= activeResultIndex && expandedResults.has(resultKey(result))
				);
				const fallbackIndex = results.findIndex((result) => expandedResults.has(resultKey(result)));
				const index = expandedIndex >= 0 ? expandedIndex : fallbackIndex;
				if (index >= 0) void toggleExpanded(results[index], index);
				return;
			}
			query = '';
			searchBar?.focus();
		}
	};

	const toggleExpanded = async (result: MailuoObjectResult, index: number) => {
		const key = resultKey(result);
		const next = new Set(expandedResults);
		if (next.has(key)) {
			jumpToResult(index, 'auto');
			next.delete(key);
		} else {
			next.add(key);
		}
		expandedResults = next;
		await tick();
		updateActiveResult();
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
		if (scrollFrame !== undefined) window.cancelAnimationFrame(scrollFrame);
		answerController?.abort();
	});
</script>

<svelte:head>
	<title>脉络</title>
</svelte:head>

<div
	bind:this={resultViewport}
	on:scroll={onResultsScroll}
	class="h-full w-full min-w-0 max-w-full overflow-y-auto {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''}"
>
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
			bind:sort
			bind:intent
			bind:modelId={selectedModelId}
			{answerModels}
			{loading}
			on:submit={(event) => execute(event.detail.intent)}
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
				loading={searchLoading}
				{error}
				{degraded}
				{warnings}
				empty={intent === 'search' && !initial && results.length === 0}
			/>

			{#if intent === 'answer' && (answerLoading || answer || answerError)}
				<AnswerCard
					question={answerQuestion}
					content={answer}
					loading={answerLoading}
					error={answerError}
					modelName={selectedModel?.name || selectedModel?.id || ''}
					results={answerResults}
					resultMode={answerResultMode}
					previousTurns={answerTurns}
					on:stop={() => answerController?.abort()}
					on:retry={() => executeAnswer(true, answerQuestion || query, 'retry')}
					on:followup={(event) => executeAnswer(true, event.detail.query, 'followup')}
					on:citation={(event) => showAnswerCitation(event.detail)}
				/>
			{/if}

			{#if results.length > 0}
				<div class="mb-3 flex items-center justify-between gap-3 px-1">
					<h2
						id="mailuo-results-heading"
						class="text-sm font-medium text-gray-700 dark:text-gray-200"
					>
						{results.length} 条{intent === 'answer' ? '依据' : '结果'}
					</h2>
					<div class="text-xs text-gray-400" aria-live="polite">
						{resultMode === 'hybrid'
							? '混合检索'
							: resultMode === 'keyword'
								? '关键词检索'
								: '语义检索'}
					</div>
				</div>
				<div
					class="divide-y divide-gray-100 rounded-2xl border border-gray-200 bg-white transition-opacity duration-200 motion-reduce:transition-none dark:divide-gray-800 dark:border-gray-800 dark:bg-gray-900 {loading
						? 'opacity-60'
						: ''}"
				>
					{#each results as result, index (result.source + ':' + result.source_object_id)}
						<div
							data-mailuo-result-index={index}
							tabindex="-1"
							class="scroll-mt-4 rounded-[inherit] outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gray-500"
						>
							<SearchResult
								{result}
								query={resultQuery}
								mode={resultMode}
								sourceName={sourceLabel(result.source, sourceLabels)}
								expanded={expandedResults.has(resultKey(result))}
								on:toggle={() => toggleExpanded(result, index)}
							/>
						</div>
					{/each}
				</div>
				<ResultQuickNav
					{results}
					{sourceLabels}
					activeIndex={activeResultIndex}
					on:select={(event) => jumpToResult(event.detail.index)}
				/>
			{/if}
		</section>
	</main>
</div>
