import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from pgvector import Vector


def load_external_module():
    config_module = types.ModuleType('open_webui.config')
    config_module.RAG_EMBEDDING_QUERY_PREFIX = ''

    class FakeConfig:
        @staticmethod
        async def get(_key, default=None):
            return default

    models_config_module = types.ModuleType('open_webui.models.config')
    models_config_module.Config = FakeConfig

    knowledge_module = types.ModuleType('open_webui.models.knowledge')
    knowledge_module.KnowledgeModel = object

    previous = {
        name: sys.modules.get(name)
        for name in ('open_webui.config', 'open_webui.models.config', 'open_webui.models.knowledge')
    }
    sys.modules['open_webui.config'] = config_module
    sys.modules['open_webui.models.config'] = models_config_module
    sys.modules['open_webui.models.knowledge'] = knowledge_module

    path = Path(__file__).parents[2] / 'open_webui' / 'retrieval' / 'external.py'
    spec = importlib.util.spec_from_file_location('mailuo_external_under_test', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    for name, original in previous.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original

    return module


class FakeCursor:
    def __init__(self):
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _query, params):
        self.params = params

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self._cursor


@pytest.mark.asyncio
async def test_pgvector_query_adapts_embedding_list_to_vector(monkeypatch):
    external = load_external_module()
    cursor = FakeCursor()

    monkeypatch.setattr(psycopg, 'connect', lambda *_a, **_k: FakeConnection(cursor))
    monkeypatch.setattr('pgvector.psycopg.register_vector', lambda _connection: None)

    knowledge = SimpleNamespace(
        id='knowledge-id',
        name='脉络',
        meta={
            'external': {
                'source': {
                    'name': 'research-docs',
                    'config': {
                        'table_name': 'public.open_webui_chunks',
                        'collection_field': 'collection_name',
                        'content_field': 'text',
                        'vector_field': 'vector',
                        'metadata_field': 'vmetadata',
                        'document_id_field': 'id',
                    },
                }
            }
        },
    )

    async def embedding_function(_query, prefix=''):
        assert prefix == ''
        return [0.1, 0.2, 0.3]

    await external._retrieve_pgvector(
        {'endpoint': 'postgresql://redacted', 'config': {}},
        {},
        knowledge,
        '测试查询',
        5,
        embedding_function,
    )

    assert isinstance(cursor.params[0], Vector)
    assert cursor.params[0].to_list() == pytest.approx([0.1, 0.2, 0.3])
    assert cursor.params[1:] == ('research-docs', 5)
