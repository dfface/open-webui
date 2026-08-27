import asyncio
from collections.abc import Callable
from typing import Any

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from open_webui.mailuo.errors import MailuoDatabaseError
from open_webui.mailuo.schemas import MailuoChunkMatch, SearchMode, SourceFacet

SEARCH_SQL = 'SELECT * FROM public.mailuo_hybrid_search(%s, %s, %s, %s, %s, %s)'
FACETS_SQL = 'SELECT * FROM public.mailuo_source_facets()'


class MailuoPostgresGateway:
    def __init__(
        self,
        knowledge_id: str,
        endpoint: str,
        timeout: int = 30,
        *,
        connect: Callable[..., Any] | None = None,
        register: Callable[[Any], None] | None = None,
    ):
        self.knowledge_id = knowledge_id
        self._endpoint = endpoint
        self._timeout = timeout
        self._connect = connect or psycopg.connect
        self._register = register or register_vector

    def _query(self, sql: str, params=None) -> list[dict[str, Any]]:
        try:
            with self._connect(
                self._endpoint,
                row_factory=dict_row,
                connect_timeout=self._timeout,
            ) as connection:
                self._register(connection)
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
        except Exception as exc:
            raise MailuoDatabaseError('Mailuo database query failed') from exc

    async def search(
        self,
        query: str,
        query_embedding: list[float] | None,
        mode: SearchMode,
        sources: list[str] | None,
    ) -> list[MailuoChunkMatch]:
        vector = Vector(query_embedding) if query_embedding is not None else None
        rows = await asyncio.to_thread(
            self._query,
            SEARCH_SQL,
            (query, vector, mode.value, sources, 150, 60),
        )
        return [MailuoChunkMatch(knowledge_id=self.knowledge_id, **row) for row in rows]

    async def facets(self) -> list[SourceFacet]:
        rows = await asyncio.to_thread(self._query, FACETS_SQL)
        return [SourceFacet(**row) for row in rows]
