import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from open_webui.mailuo.errors import MailuoDatabaseError, MailuoForbiddenError
from open_webui.mailuo.schemas import (
    MailuoFacetResponse,
    MailuoFacetRequest,
    MailuoKnowledge,
    MailuoSearchRequest,
    MailuoSearchResponse,
    SearchMode,
    SourceFacet,
)


def load_router_module():
    internal_db = types.ModuleType('open_webui.internal.db')

    async def get_async_session():
        yield None

    internal_db.get_async_session = get_async_session

    auth = types.ModuleType('open_webui.utils.auth')

    async def get_verified_user():
        return SimpleNamespace(id='user-1', role='user')

    auth.get_verified_user = get_verified_user

    previous = {
        name: sys.modules.get(name)
        for name in ('open_webui.internal.db', 'open_webui.utils.auth')
    }
    sys.modules['open_webui.internal.db'] = internal_db
    sys.modules['open_webui.utils.auth'] = auth

    path = Path(__file__).parents[2] / 'open_webui' / 'mailuo' / 'router.py'
    spec = importlib.util.spec_from_file_location('mailuo_router_under_test', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    for name, original in previous.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original
    return module


class FakeService:
    def __init__(self, error=None):
        self.error = error

    async def search(self, request, form, user, db=None):
        if self.error:
            raise self.error
        return MailuoSearchResponse(
            requested_mode=form.mode,
            executed_mode=form.mode,
            results=[],
        )

    async def facets(self, knowledge_ids, user, db=None):
        if self.error:
            raise self.error
        return MailuoFacetResponse(
            sources=[SourceFacet(source='future', display_name='future', object_count=1)]
        )


@pytest.mark.asyncio
async def test_router_exposes_knowledge_facets_and_search_contract(monkeypatch):
    module = load_router_module()
    monkeypatch.setattr(module, 'service', FakeService())
    monkeypatch.setattr(
        module,
        'list_accessible_mailuo_knowledges',
        lambda *_args, **_kwargs: async_value(
            [MailuoKnowledge(id='kb-1', name='脉络', description='')]
        ),
    )
    user = SimpleNamespace(id='user-1', role='user')
    request = SimpleNamespace(headers={})

    knowledges = await module.get_mailuo_knowledges(user=user, db=None)
    facets = await module.get_mailuo_facets(
        MailuoFacetRequest(knowledge_ids=['kb-1']),
        user=user,
        db=None,
    )
    search = await module.search_mailuo(
        request,
        MailuoSearchRequest(query='统一搜索', mode='hybrid', knowledge_ids=['kb-1']),
        user=user,
        db=None,
    )

    assert knowledges == [MailuoKnowledge(id='kb-1', name='脉络', description='')]
    assert facets.sources[0].source == 'future'
    assert search.requested_mode == SearchMode.HYBRID


@pytest.mark.asyncio
async def test_router_maps_forbidden_and_database_errors_without_leaking_details(monkeypatch):
    module = load_router_module()
    request = SimpleNamespace(headers={'x-request-id': 'request-1'})
    form = MailuoSearchRequest(query='x')
    user = SimpleNamespace(id='user-1', role='user')

    monkeypatch.setattr(module, 'service', FakeService(MailuoForbiddenError('private grant detail')))
    with pytest.raises(HTTPException) as forbidden_info:
        await module.search_mailuo(request, form, user=user, db=None)
    forbidden = forbidden_info.value
    assert forbidden.status_code == 403
    assert forbidden.detail['message'] == 'Knowledge is not accessible'
    assert forbidden.detail['request_id'] == 'request-1'
    assert 'private grant detail' not in str(forbidden.detail)

    monkeypatch.setattr(
        module,
        'service',
        FakeService(MailuoDatabaseError('postgresql://secret-host password=secret')),
    )
    with pytest.raises(HTTPException) as unavailable_info:
        await module.search_mailuo(request, form, user=user, db=None)
    unavailable = unavailable_info.value
    assert unavailable.status_code == 503
    assert unavailable.detail['message'] == 'Mailuo search is temporarily unavailable'
    assert 'secret-host' not in str(unavailable.detail)
    assert 'password' not in str(unavailable.detail)


async def async_value(value):
    return value
