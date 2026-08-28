import datetime as dt
import enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SearchMode(enum.StrEnum):
    HYBRID = 'hybrid'
    KEYWORD = 'keyword'
    SEMANTIC = 'semantic'


class SearchSort(enum.StrEnum):
    RELEVANCE = 'relevance'
    UPDATED_DESC = 'updated_desc'
    UPDATED_ASC = 'updated_asc'


def _deduplicate(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class MailuoSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.HYBRID
    knowledge_ids: list[str] | None = None
    sources: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=150)
    sort: SearchSort = SearchSort.RELEVANCE

    @field_validator('query')
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('query must not be empty')
        return value

    @field_validator('knowledge_ids', 'sources')
    @classmethod
    def normalize_filters(cls, value: list[str] | None) -> list[str] | None:
        return _deduplicate(value)


class MailuoConversationMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=4000)

    @field_validator('content')
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('content must not be empty')
        return value


class MailuoAnswerRequest(MailuoSearchRequest):
    model: str = Field(min_length=1, max_length=512)
    limit: int = Field(default=8, ge=1, le=12)
    history: list[MailuoConversationMessage] = Field(default_factory=list, max_length=8)

    @field_validator('model')
    @classmethod
    def normalize_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('model must not be empty')
        return value


class MailuoFacetRequest(BaseModel):
    knowledge_ids: list[str] | None = None

    @field_validator('knowledge_ids')
    @classmethod
    def normalize_knowledge_ids(cls, value: list[str] | None) -> list[str] | None:
        return _deduplicate(value)


class MailuoKnowledge(BaseModel):
    id: str
    name: str
    description: str = ''


class SourceFacet(BaseModel):
    source: str
    display_name: str
    color: str | None = None
    object_count: int = 0


class MailuoChunkMatch(BaseModel):
    knowledge_id: str
    source: str
    source_object_id: str
    chunk_no: int
    title: str
    content: str
    source_url: str
    source_updated_at: dt.datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float
    matched_by: list[str] = Field(default_factory=list)


class MailuoSnippet(BaseModel):
    chunk_no: int
    content: str
    matched_by: list[str] = Field(default_factory=list)


class MailuoObjectResult(BaseModel):
    knowledge_ids: list[str]
    source: str
    source_object_id: str
    title: str
    source_url: str
    source_updated_at: dt.datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    matched_by: list[str]
    matches: list[MailuoSnippet]
    score: float = Field(exclude=True)


class MailuoSearchResponse(BaseModel):
    requested_mode: SearchMode
    executed_mode: SearchMode
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)
    results: list[MailuoObjectResult] = Field(default_factory=list)


class MailuoFacetResponse(BaseModel):
    sources: list[SourceFacet] = Field(default_factory=list)
