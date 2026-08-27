from types import SimpleNamespace

import pytest

from open_webui.mailuo.errors import MailuoConfigurationError, MailuoForbiddenError
from open_webui.mailuo.knowledge import list_accessible_mailuo_knowledges, resolve_mailuo_knowledges


class FakeKnowledgeStore:
    def __init__(self, knowledges, access=None):
        self.knowledges = {knowledge.id: knowledge for knowledge in knowledges}
        self.access = access or {}

    async def get_knowledge_bases(self, db=None):
        return list(self.knowledges.values())

    async def get_knowledge_by_id(self, knowledge_id, db=None):
        return self.knowledges.get(knowledge_id)

    async def check_access_by_user_id(self, knowledge_id, user_id, permission='read', db=None):
        return self.access.get((knowledge_id, user_id, permission), False)


def knowledge(knowledge_id, connection_id='connection-1', owner='owner'):
    return SimpleNamespace(
        id=knowledge_id,
        name=f'Knowledge {knowledge_id}',
        description='',
        user_id=owner,
        meta={'source': 'external', 'external': {'connection_id': connection_id}},
    )


async def get_connections():
    return [
        {
            'id': 'connection-1',
            'provider': 'pgvector',
            'endpoint': 'postgresql://redacted',
            'enabled': True,
            'config': {'timeout': 12},
        },
        {
            'id': 'connection-disabled',
            'provider': 'pgvector',
            'endpoint': 'postgresql://disabled',
            'enabled': False,
        },
        {
            'id': 'connection-qdrant',
            'provider': 'qdrant',
            'endpoint': 'https://qdrant.example',
            'enabled': True,
        },
    ]


@pytest.mark.asyncio
async def test_list_returns_only_accessible_enabled_pgvector_knowledge():
    items = [
        knowledge('owned'),
        knowledge('granted', owner='someone-else'),
        knowledge('denied', owner='someone-else'),
        knowledge('disabled', 'connection-disabled'),
        knowledge('qdrant', 'connection-qdrant'),
    ]
    store = FakeKnowledgeStore(items, {('granted', 'user-1', 'read'): True})
    user = SimpleNamespace(id='user-1', role='user')

    result = await list_accessible_mailuo_knowledges(
        user,
        knowledge_store=store,
        get_connections=get_connections,
    )

    assert [item.id for item in result] == ['granted']


@pytest.mark.asyncio
async def test_owner_and_admin_can_resolve_pgvector_knowledge():
    item = knowledge('kb-1', owner='owner')
    store = FakeKnowledgeStore([item])

    owner_result = await resolve_mailuo_knowledges(
        ['kb-1'],
        SimpleNamespace(id='owner', role='user'),
        knowledge_store=store,
        get_connections=get_connections,
    )
    admin_result = await resolve_mailuo_knowledges(
        ['kb-1'],
        SimpleNamespace(id='admin', role='admin'),
        knowledge_store=store,
        get_connections=get_connections,
    )

    assert owner_result[0].endpoint == 'postgresql://redacted'
    assert owner_result[0].timeout == 12
    assert admin_result[0].id == 'kb-1'


@pytest.mark.asyncio
async def test_explicit_inaccessible_knowledge_is_forbidden():
    store = FakeKnowledgeStore([knowledge('kb-1', owner='other')])

    with pytest.raises(MailuoForbiddenError):
        await resolve_mailuo_knowledges(
            ['kb-1'],
            SimpleNamespace(id='user-1', role='user'),
            knowledge_store=store,
            get_connections=get_connections,
        )


@pytest.mark.asyncio
async def test_non_pgvector_knowledge_is_not_mailuo_compatible():
    store = FakeKnowledgeStore([knowledge('kb-1', 'connection-qdrant')])

    with pytest.raises(MailuoConfigurationError):
        await resolve_mailuo_knowledges(
            ['kb-1'],
            SimpleNamespace(id='admin', role='admin'),
            knowledge_store=store,
            get_connections=get_connections,
        )
