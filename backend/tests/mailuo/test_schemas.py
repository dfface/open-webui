import pytest
from open_webui.mailuo.schemas import MailuoAnswerRequest, MailuoSearchRequest, SearchMode
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


def test_keyword_search_accepts_full_candidate_limit():
    request = MailuoSearchRequest(query='架构', mode='keyword', limit=150)

    assert request.mode == SearchMode.KEYWORD
    assert request.limit == 150


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


@pytest.mark.parametrize(
    ('payload', 'field'),
    [
        ({'query': '   '}, 'query'),
        ({'query': 'x', 'mode': 'unknown'}, 'mode'),
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
