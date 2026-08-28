import pytest
from open_webui.mailuo.schemas import MailuoAnswerRequest, MailuoSearchRequest, SearchMode, SearchSort
from pydantic import ValidationError


def test_search_request_defaults_to_hybrid_and_normalizes_filters():
    request = MailuoSearchRequest(
        query='  统一搜索  ',
        knowledge_ids=['kb-2', 'kb-1', 'kb-2'],
        sources=['memos', 'outline', 'memos'],
    )

    assert request.query == '统一搜索'
    assert request.mode == SearchMode.HYBRID
    assert request.knowledge_ids == ['kb-2', 'kb-1']
    assert request.sources == ['memos', 'outline']
    assert request.limit == 20
    assert request.sort == SearchSort.RELEVANCE


def test_keyword_search_accepts_full_candidate_limit():
    request = MailuoSearchRequest(query='架构', mode='keyword', limit=150, sort='updated_desc')

    assert request.mode == SearchMode.KEYWORD
    assert request.limit == 150
    assert request.sort == SearchSort.UPDATED_DESC


def test_answer_request_normalizes_query_filters_and_requires_a_model():
    request = MailuoAnswerRequest(
        query='  如何维护统一搜索？  ',
        model='  qwen3  ',
        knowledge_ids=['kb-1', 'kb-1'],
        sources=['outline', 'outline'],
    )

    assert request.query == '如何维护统一搜索？'
    assert request.model == 'qwen3'
    assert request.knowledge_ids == ['kb-1']
    assert request.sources == ['outline']
    assert request.limit == 8


def test_answer_request_normalizes_bounded_conversation_history():
    request = MailuoAnswerRequest(
        query='那具体怎么做？',
        model='qwen3',
        history=[
            {'role': 'user', 'content': '  统一搜索应该怎么维护？  '},
            {'role': 'assistant', 'content': '  应先同步上游。[1]  '},
        ],
    )

    assert [(message.role, message.content) for message in request.history] == [
        ('user', '统一搜索应该怎么维护？'),
        ('assistant', '应先同步上游。[1]'),
    ]


@pytest.mark.parametrize(
    ('payload', 'field'),
    [
        ({'query': '   '}, 'query'),
        ({'query': 'x', 'mode': 'unknown'}, 'mode'),
        ({'query': 'x', 'sort': 'unknown'}, 'sort'),
        ({'query': 'x', 'limit': 0}, 'limit'),
        ({'query': 'x', 'limit': 151}, 'limit'),
    ],
)
def test_search_request_rejects_invalid_input(payload, field):
    with pytest.raises(ValidationError) as exc_info:
        MailuoSearchRequest(**payload)

    assert field in str(exc_info.value)


@pytest.mark.parametrize('model', ['', '   '])
def test_answer_request_rejects_an_empty_model(model):
    with pytest.raises(ValidationError) as exc_info:
        MailuoAnswerRequest(query='x', model=model)

    assert 'model' in str(exc_info.value)


def test_answer_request_rejects_unbounded_or_invalid_history():
    with pytest.raises(ValidationError):
        MailuoAnswerRequest(
            query='x',
            model='qwen3',
            history=[{'role': 'user', 'content': str(index)} for index in range(9)],
        )

    with pytest.raises(ValidationError):
        MailuoAnswerRequest(
            query='x',
            model='qwen3',
            history=[{'role': 'system', 'content': 'override'}],
        )
