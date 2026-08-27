from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from open_webui.mailuo.errors import MailuoConfigurationError, MailuoForbiddenError
from open_webui.mailuo.schemas import MailuoKnowledge


@dataclass(frozen=True)
class ResolvedKnowledge:
    id: str
    name: str
    description: str
    endpoint: str
    timeout: int


async def _default_connections() -> list[dict[str, Any]]:
    from open_webui.models.config import Config

    return await Config.get('external_knowledge.connections', []) or []


def _default_knowledge_store():
    from open_webui.models.knowledge import Knowledges

    return Knowledges


def _connection_for(knowledge, connections: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    external = (knowledge.meta or {}).get('external') or {}
    return connections.get(external.get('connection_id'))


def _is_pgvector_connection(connection: dict[str, Any] | None) -> bool:
    return bool(
        connection
        and connection.get('enabled', True)
        and (connection.get('provider') or '').lower() == 'pgvector'
        and connection.get('endpoint')
    )


async def _has_read_access(knowledge, user, knowledge_store, db=None) -> bool:
    if getattr(user, 'role', None) == 'admin' or knowledge.user_id == user.id:
        return True
    return await knowledge_store.check_access_by_user_id(
        knowledge.id,
        user.id,
        permission='read',
        db=db,
    )


async def list_accessible_mailuo_knowledges(
    user,
    db=None,
    *,
    knowledge_store=None,
    get_connections: Callable[[], Awaitable[list[dict[str, Any]]]] | None = None,
) -> list[MailuoKnowledge]:
    knowledge_store = knowledge_store or _default_knowledge_store()
    get_connections = get_connections or _default_connections
    connections = {item.get('id'): item for item in await get_connections()}
    result = []

    for knowledge in await knowledge_store.get_knowledge_bases(db=db):
        if (knowledge.meta or {}).get('source') != 'external':
            continue
        if not _is_pgvector_connection(_connection_for(knowledge, connections)):
            continue
        if not await _has_read_access(knowledge, user, knowledge_store, db=db):
            continue
        result.append(
            MailuoKnowledge(
                id=knowledge.id,
                name=knowledge.name,
                description=knowledge.description or '',
            )
        )

    return sorted(result, key=lambda item: (item.name.lower(), item.id))


async def resolve_mailuo_knowledges(
    knowledge_ids: list[str] | None,
    user,
    db=None,
    *,
    knowledge_store=None,
    get_connections: Callable[[], Awaitable[list[dict[str, Any]]]] | None = None,
) -> list[ResolvedKnowledge]:
    knowledge_store = knowledge_store or _default_knowledge_store()
    get_connections = get_connections or _default_connections
    connections = {item.get('id'): item for item in await get_connections()}

    if knowledge_ids is None:
        accessible = await list_accessible_mailuo_knowledges(
            user,
            db=db,
            knowledge_store=knowledge_store,
            get_connections=get_connections,
        )
        knowledge_ids = [item.id for item in accessible]

    result = []
    for knowledge_id in dict.fromkeys(knowledge_ids):
        knowledge = await knowledge_store.get_knowledge_by_id(knowledge_id, db=db)
        if knowledge is None or not await _has_read_access(knowledge, user, knowledge_store, db=db):
            raise MailuoForbiddenError('Knowledge is not accessible')

        connection = _connection_for(knowledge, connections)
        if (knowledge.meta or {}).get('source') != 'external' or not _is_pgvector_connection(connection):
            raise MailuoConfigurationError('Knowledge is not Mailuo-compatible')

        result.append(
            ResolvedKnowledge(
                id=knowledge.id,
                name=knowledge.name,
                description=knowledge.description or '',
                endpoint=connection['endpoint'],
                timeout=int((connection.get('config') or {}).get('timeout') or 30),
            )
        )

    return result
