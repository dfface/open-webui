import pytest
from pydantic import ValidationError

from open_webui.mailuo.schemas import MailuoSearchRequest, SearchMode


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


@pytest.mark.parametrize(
    ('payload', 'field'),
    [
        ({'query': '   '}, 'query'),
        ({'query': 'x', 'mode': 'unknown'}, 'mode'),
        ({'query': 'x', 'limit': 0}, 'limit'),
        ({'query': 'x', 'limit': 51}, 'limit'),
    ],
)
def test_search_request_rejects_invalid_input(payload, field):
    with pytest.raises(ValidationError) as exc_info:
        MailuoSearchRequest(**payload)

    assert field in str(exc_info.value)
