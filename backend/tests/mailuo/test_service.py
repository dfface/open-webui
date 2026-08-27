from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from open_webui.mailuo.errors import MailuoDatabaseError, MailuoEmbeddingError, MailuoSearchError
from open_webui.mailuo.knowledge import ResolvedKnowledge
from open_webui.mailuo.schemas import MailuoChunkMatch, MailuoSearchRequest, SearchMode, SourceFacet
from open_webui.mailuo.service import MailuoSearchService


def match(knowledge_id, object_id, score):
    return MailuoChunkMatch(
        knowledge_id=knowledge_id,
        source='outline',
        source_object_id=object_id,
        chunk_no=0,
        title=object_id,
        content=f'content {object_id}',
        source_url=f'https://example.test/{object_id}',
        source_updated_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
        metadata={},
        score=score,
        matched_by=['semantic'],
    )


class FakeGateway:
    def __init__(self, knowledge_id, rows=None, error=None, facets=None):
        self.knowledge_id = knowledge_id
        self.rows = rows or []
        self.error = error
        self.source_facets = facets or []
        self.calls = []

    async def search(self, query, query_embedding, mode, sources):
        self.calls.append((query, query_embedding, mode, sources))
        if self.error:
            raise self.error
        return self.rows

    async def facets(self):
        if self.error:
            raise self.error
        return self.source_facets


def resolved(knowledge_id):
    return ResolvedKnowledge(
        id=knowledge_id,
        name=knowledge_id,
        description='',
        endpoint='postgresql://redacted',
        timeout=30,
    )


@pytest.mark.asyncio
async def test_keyword_search_bypasses_embedding():
    gateway = FakeGateway('kb-1', [match('kb-1', 'keyword', 0.4)])
    embedding_calls = 0

    async def embed(*_args):
        nonlocal embedding_calls
        embedding_calls += 1
        return [1.0]

    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('kb-1')]),
        gateway_factory=lambda _knowledge: gateway,
        embed=embed,
    )

    response = await service.search(
        SimpleNamespace(),
        MailuoSearchRequest(query='keyword', mode='keyword'),
        SimpleNamespace(id='user-1'),
    )

    assert embedding_calls == 0
    assert gateway.calls[0][1] is None
    assert response.executed_mode == SearchMode.KEYWORD


@pytest.mark.asyncio
async def test_hybrid_reuses_one_embedding_for_all_knowledges_and_deduplicates_objects():
    gateways = {
        'kb-1': FakeGateway('kb-1', [match('kb-1', 'same', 0.8)]),
        'kb-2': FakeGateway('kb-2', [match('kb-2', 'same', 0.7), match('kb-2', 'other', 0.6)]),
    }
    embedding_calls = 0

    async def embed(*_args):
        nonlocal embedding_calls
        embedding_calls += 1
        return [0.1, 0.2]

    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('kb-1'), resolved('kb-2')]),
        gateway_factory=lambda knowledge: gateways[knowledge.id],
        embed=embed,
    )

    response = await service.search(
        SimpleNamespace(),
        MailuoSearchRequest(query='hybrid'),
        SimpleNamespace(id='user-1'),
    )

    assert embedding_calls == 1
    assert gateways['kb-1'].calls[0][1] == [0.1, 0.2]
    assert gateways['kb-2'].calls[0][1] == [0.1, 0.2]
    assert [item.source_object_id for item in response.results] == ['same', 'other']
    assert response.results[0].knowledge_ids == ['kb-1', 'kb-2']


@pytest.mark.asyncio
async def test_hybrid_embedding_failure_degrades_to_keyword():
    gateway = FakeGateway('kb-1', [match('kb-1', 'fallback', 0.5)])

    async def fail_embed(*_args):
        raise MailuoEmbeddingError('Query embedding failed')

    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('kb-1')]),
        gateway_factory=lambda _knowledge: gateway,
        embed=fail_embed,
    )

    response = await service.search(
        SimpleNamespace(),
        MailuoSearchRequest(query='hybrid'),
        SimpleNamespace(id='user-1'),
    )

    assert response.requested_mode == SearchMode.HYBRID
    assert response.executed_mode == SearchMode.KEYWORD
    assert response.degraded is True
    assert response.warnings == ['语义检索暂时不可用，已降级为关键词检索。']
    assert gateway.calls[0][1] is None


@pytest.mark.asyncio
async def test_semantic_embedding_failure_does_not_silently_degrade():
    async def fail_embed(*_args):
        raise MailuoEmbeddingError('Query embedding failed')

    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('kb-1')]),
        gateway_factory=lambda knowledge: FakeGateway(knowledge.id),
        embed=fail_embed,
    )

    with pytest.raises(MailuoEmbeddingError):
        await service.search(
            SimpleNamespace(),
            MailuoSearchRequest(query='semantic', mode='semantic'),
            SimpleNamespace(id='user-1'),
        )


@pytest.mark.asyncio
async def test_one_knowledge_failure_returns_partial_results_and_all_failures_raise():
    gateways = {
        'good': FakeGateway('good', [match('good', 'found', 0.4)]),
        'bad': FakeGateway('bad', error=MailuoDatabaseError('Mailuo database query failed')),
    }
    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('good'), resolved('bad')]),
        gateway_factory=lambda knowledge: gateways[knowledge.id],
        embed=lambda *_args: async_value([1.0]),
    )

    response = await service.search(
        SimpleNamespace(),
        MailuoSearchRequest(query='partial'),
        SimpleNamespace(id='user-1'),
    )

    assert [item.source_object_id for item in response.results] == ['found']
    assert response.warnings == ['知识库 bad 暂时不可用。']

    gateways['good'].error = MailuoDatabaseError('Mailuo database query failed')
    with pytest.raises(MailuoSearchError):
        await service.search(
            SimpleNamespace(),
            MailuoSearchRequest(query='all fail'),
            SimpleNamespace(id='user-1'),
        )


@pytest.mark.asyncio
async def test_facets_merge_unknown_sources_without_double_counting_duplicate_knowledge():
    gateways = {
        'kb-1': FakeGateway(
            'kb-1',
            facets=[SourceFacet(source='future', display_name='future', object_count=3)],
        ),
        'kb-2': FakeGateway(
            'kb-2',
            facets=[SourceFacet(source='future', display_name='Future', object_count=3)],
        ),
    }
    service = MailuoSearchService(
        resolve=lambda *_args, **_kwargs: async_value([resolved('kb-1'), resolved('kb-2')]),
        gateway_factory=lambda knowledge: gateways[knowledge.id],
        embed=lambda *_args: async_value([1.0]),
    )

    response = await service.facets(None, SimpleNamespace(id='user-1'))

    assert len(response.sources) == 1
    assert response.sources[0].source == 'future'
    assert response.sources[0].object_count == 3


async def async_value(value):
    return value
