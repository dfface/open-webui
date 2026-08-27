import asyncio
import logging
import time
from collections.abc import Callable

from open_webui.mailuo.embedding import generate_query_embedding
from open_webui.mailuo.errors import MailuoEmbeddingError, MailuoSearchError
from open_webui.mailuo.knowledge import resolve_mailuo_knowledges
from open_webui.mailuo.postgres import MailuoPostgresGateway
from open_webui.mailuo.ranking import aggregate_chunk_matches
from open_webui.mailuo.schemas import (
    MailuoFacetResponse,
    MailuoSearchRequest,
    MailuoSearchResponse,
    SearchMode,
    SourceFacet,
)

log = logging.getLogger(__name__)


class MailuoSearchService:
    def __init__(
        self,
        *,
        resolve=resolve_mailuo_knowledges,
        gateway_factory: Callable | None = None,
        embed=generate_query_embedding,
    ):
        self._resolve = resolve
        self._gateway_factory = gateway_factory or (
            lambda knowledge: MailuoPostgresGateway(
                knowledge_id=knowledge.id,
                endpoint=knowledge.endpoint,
                timeout=knowledge.timeout,
            )
        )
        self._embed = embed

    async def search(self, http_request, form: MailuoSearchRequest, user, db=None) -> MailuoSearchResponse:
        started_at = time.monotonic()
        knowledges = await self._resolve(form.knowledge_ids, user, db=db)
        if not knowledges:
            raise MailuoSearchError('No accessible Mailuo knowledge')

        executed_mode = form.mode
        degraded = False
        warnings = []
        query_embedding = None

        if form.mode != SearchMode.KEYWORD:
            try:
                query_embedding = await self._embed(http_request, form.query, user)
            except MailuoEmbeddingError:
                if form.mode == SearchMode.SEMANTIC:
                    raise
                executed_mode = SearchMode.KEYWORD
                degraded = True
                warnings.append('语义检索暂时不可用，已降级为关键词检索。')

        gateways = [self._gateway_factory(knowledge) for knowledge in knowledges]
        outcomes = await asyncio.gather(
            *(
                gateway.search(
                    form.query,
                    query_embedding,
                    executed_mode,
                    form.sources,
                )
                for gateway in gateways
            ),
            return_exceptions=True,
        )

        rows = []
        successful_queries = 0
        for knowledge, outcome in zip(knowledges, outcomes):
            if isinstance(outcome, Exception):
                warnings.append(f'知识库 {knowledge.name} 暂时不可用。')
                log.warning(
                    'mailuo_knowledge_search_failed knowledge_id=%s error_class=%s',
                    knowledge.id,
                    type(outcome).__name__,
                )
                continue
            successful_queries += 1
            rows.extend(outcome)

        if successful_queries == 0:
            raise MailuoSearchError('All Mailuo knowledge searches failed')

        results = aggregate_chunk_matches(rows, limit=form.limit, snippets_per_object=3)
        log.info(
            'mailuo_search requested_mode=%s executed_mode=%s degraded=%s '
            'knowledge_count=%s result_count=%s latency_ms=%s',
            form.mode.value,
            executed_mode.value,
            degraded,
            len(knowledges),
            len(results),
            round((time.monotonic() - started_at) * 1000),
        )
        return MailuoSearchResponse(
            requested_mode=form.mode,
            executed_mode=executed_mode,
            degraded=degraded,
            warnings=warnings,
            results=results,
        )

    async def facets(self, knowledge_ids: list[str] | None, user, db=None) -> MailuoFacetResponse:
        knowledges = await self._resolve(knowledge_ids, user, db=db)
        if not knowledges:
            return MailuoFacetResponse()

        gateways = [self._gateway_factory(knowledge) for knowledge in knowledges]
        outcomes = await asyncio.gather(*(gateway.facets() for gateway in gateways), return_exceptions=True)
        merged: dict[str, SourceFacet] = {}
        successful_queries = 0
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                continue
            successful_queries += 1
            for facet in outcome:
                current = merged.get(facet.source)
                if current is None:
                    merged[facet.source] = facet
                else:
                    current.object_count = max(current.object_count, facet.object_count)
                    if current.display_name == current.source and facet.display_name != facet.source:
                        current.display_name = facet.display_name
                    current.color = current.color or facet.color

        if successful_queries == 0:
            raise MailuoSearchError('All Mailuo facet queries failed')

        return MailuoFacetResponse(
            sources=sorted(merged.values(), key=lambda facet: (facet.display_name.lower(), facet.source))
        )
