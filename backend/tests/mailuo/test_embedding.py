import asyncio
from types import SimpleNamespace

import pytest
from open_webui.mailuo.embedding import generate_query_embedding
from open_webui.mailuo.errors import MailuoEmbeddingError


class FakeRedisLock:
    def __init__(self, mutex, state):
        self.mutex = mutex
        self.state = state

    async def acquire(self):
        await self.mutex.acquire()
        self.state['active'] += 1
        self.state['maximum'] = max(self.state['maximum'], self.state['active'])
        return True

    async def release(self):
        self.state['active'] -= 1
        self.mutex.release()


class FakeRedis:
    def __init__(self):
        self.mutex = asyncio.Lock()
        self.state = {'active': 0, 'maximum': 0}
        self.calls = []

    def lock(self, name, timeout, blocking_timeout):
        self.calls.append((name, timeout, blocking_timeout))
        return FakeRedisLock(self.mutex, self.state)


@pytest.mark.asyncio
async def test_query_embeddings_are_serialized_by_redis_lock():
    redis = FakeRedis()
    active_embeddings = 0
    maximum_embeddings = 0

    async def embedding_function(query, prefix, user):
        nonlocal active_embeddings, maximum_embeddings
        active_embeddings += 1
        maximum_embeddings = max(maximum_embeddings, active_embeddings)
        await asyncio.sleep(0.01)
        active_embeddings -= 1
        return [float(len(query))]

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(redis=redis, EMBEDDING_FUNCTION=embedding_function))
    )
    user = SimpleNamespace(id='user-1')

    results = await asyncio.gather(
        generate_query_embedding(request, 'first', user, prefix='query:'),
        generate_query_embedding(request, 'second', user, prefix='query:'),
    )

    assert results == [[5.0], [6.0]]
    assert maximum_embeddings == 1
    assert redis.state['maximum'] == 1
    assert redis.calls == [
        ('mailuo:embedding', 60, 15),
        ('mailuo:embedding', 60, 15),
    ]


@pytest.mark.asyncio
async def test_embedding_failure_is_wrapped_without_original_secret():
    async def embedding_function(_query, prefix, user):
        raise RuntimeError('Bearer secret-token')

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(redis=None, EMBEDDING_FUNCTION=embedding_function))
    )

    with pytest.raises(MailuoEmbeddingError) as exc_info:
        await generate_query_embedding(
            request,
            'query',
            SimpleNamespace(id='user-1'),
            prefix='',
        )

    assert str(exc_info.value) == 'Query embedding failed'
    assert 'secret-token' not in str(exc_info.value)
