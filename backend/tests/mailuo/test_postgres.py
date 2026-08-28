import datetime as dt

import pytest
from open_webui.mailuo.errors import MailuoDatabaseError
from open_webui.mailuo.postgres import MailuoPostgresGateway
from open_webui.mailuo.schemas import SearchMode
from pgvector import Vector


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_instance


@pytest.mark.asyncio
async def test_search_calls_fixed_database_function_with_vector_parameter():
    cursor = FakeCursor(
        [
            {
                'source': 'memos',
                'source_object_id': 'memo-1',
                'chunk_no': 0,
                'title': 'Memo',
                'content': 'Body',
                'source_url': 'https://memos.example/m/1',
                'source_updated_at': dt.datetime(2026, 8, 27, tzinfo=dt.UTC),
                'metadata': {},
                'score': 0.5,
                'matched_by': ['semantic'],
            }
        ]
    )
    gateway = MailuoPostgresGateway(
        knowledge_id='kb-1',
        endpoint='postgresql://redacted',
        timeout=7,
        connect=lambda *_args, **_kwargs: FakeConnection(cursor),
        register=lambda _connection: None,
    )

    rows = await gateway.search(
        query='知识脉络',
        query_embedding=[0.1, 0.2, 0.3],
        mode=SearchMode.HYBRID,
        sources=['memos'],
    )

    query, params = cursor.calls[0]
    assert str(query).startswith('SELECT * FROM public.mailuo_hybrid_search(')
    assert params[0] == '知识脉络'
    assert isinstance(params[1], Vector)
    assert params[1].to_list() == pytest.approx([0.1, 0.2, 0.3])
    assert params[2:] == ('hybrid', ['memos'], 150, 60)
    assert rows[0].knowledge_id == 'kb-1'
    assert rows[0].source == 'memos'


@pytest.mark.asyncio
async def test_facets_queries_chunks_directly_and_keeps_unknown_source():
    cursor = FakeCursor(
        [
            {
                'source': 'future_source',
                'display_name': 'future_source',
                'color': None,
                'object_count': 3,
            }
        ]
    )
    gateway = MailuoPostgresGateway(
        knowledge_id='kb-1',
        endpoint='postgresql://redacted',
        connect=lambda *_args, **_kwargs: FakeConnection(cursor),
        register=lambda _connection: None,
    )

    facets = await gateway.facets()

    query = str(cursor.calls[0][0])
    assert 'FROM public.chunks' in query
    assert 'count(DISTINCT source_object_id)' in query
    assert 'mailuo_source_facets' not in query
    assert cursor.calls[0][1] is None
    assert facets[0].source == 'future_source'


@pytest.mark.asyncio
async def test_database_errors_do_not_expose_connection_or_sql():
    def fail_connect(*_args, **_kwargs):
        raise RuntimeError('password=secret at postgresql://private-host/mailuo')

    gateway = MailuoPostgresGateway(
        knowledge_id='kb-1',
        endpoint='postgresql://private-host/mailuo',
        connect=fail_connect,
    )

    with pytest.raises(MailuoDatabaseError) as exc_info:
        await gateway.facets()

    assert str(exc_info.value) == 'Mailuo database query failed'
    assert 'private-host' not in str(exc_info.value)
    assert 'secret' not in str(exc_info.value)
