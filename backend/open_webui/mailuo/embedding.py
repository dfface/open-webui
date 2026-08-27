import asyncio
import logging
from contextlib import asynccontextmanager

from open_webui.mailuo.errors import MailuoEmbeddingError

log = logging.getLogger(__name__)

_LOCAL_EMBEDDING_LOCK = asyncio.Lock()
_warned_local_lock = False


@asynccontextmanager
async def embedding_slot(redis, *, timeout: int = 60, blocking_timeout: int = 15):
    global _warned_local_lock

    if redis is None:
        if not _warned_local_lock:
            log.warning('mailuo_embedding_lock redis_unavailable=true fallback=process_lock')
            _warned_local_lock = True
        async with _LOCAL_EMBEDDING_LOCK:
            yield
        return

    lock = redis.lock(
        'mailuo:embedding',
        timeout=timeout,
        blocking_timeout=blocking_timeout,
    )
    acquired = await lock.acquire()
    if not acquired:
        raise MailuoEmbeddingError('Embedding service is busy')
    try:
        yield
    finally:
        await lock.release()


async def generate_query_embedding(request, query: str, user, *, prefix: str | None = None) -> list[float]:
    if prefix is None:
        from open_webui.config import RAG_EMBEDDING_QUERY_PREFIX

        prefix = RAG_EMBEDDING_QUERY_PREFIX

    embedding_function = getattr(request.app.state, 'EMBEDDING_FUNCTION', None)
    if embedding_function is None:
        raise MailuoEmbeddingError('Query embedding is not configured')

    try:
        async with embedding_slot(getattr(request.app.state, 'redis', None)):
            return await embedding_function(query, prefix=prefix, user=user)
    except MailuoEmbeddingError:
        raise
    except Exception as exc:
        raise MailuoEmbeddingError('Query embedding failed') from exc
