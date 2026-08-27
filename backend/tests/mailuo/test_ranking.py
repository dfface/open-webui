import datetime as dt

from open_webui.mailuo.ranking import aggregate_chunk_matches
from open_webui.mailuo.schemas import MailuoChunkMatch


def row(
    source,
    object_id,
    chunk_no,
    score,
    updated_at,
    matched_by,
    content=None,
):
    return MailuoChunkMatch(
        knowledge_id='kb-1',
        source=source,
        source_object_id=object_id,
        chunk_no=chunk_no,
        title=f'Title {object_id}',
        content=content or f'Content {object_id}-{chunk_no}',
        source_url=f'https://example.test/{source}/{object_id}',
        source_updated_at=dt.datetime.fromisoformat(updated_at).replace(tzinfo=dt.UTC),
        metadata={},
        score=score,
        matched_by=matched_by,
    )


def test_aggregate_groups_by_source_and_object_uses_best_chunk_score():
    results = aggregate_chunk_matches(
        [
            row('outline', 'same', 0, 0.4, '2026-08-25T00:00:00', ['semantic']),
            row('outline', 'same', 1, 0.9, '2026-08-25T00:00:00', ['fulltext']),
            row('memos', 'same', 0, 0.8, '2026-08-26T00:00:00', ['trigram']),
        ],
        limit=20,
        snippets_per_object=3,
    )

    assert [(item.source, item.source_object_id) for item in results] == [
        ('outline', 'same'),
        ('memos', 'same'),
    ]
    assert results[0].score == 0.9
    assert [match.chunk_no for match in results[0].matches] == [1, 0]
    assert results[0].matched_by == ['fulltext', 'semantic']


def test_aggregate_limits_objects_and_snippets_with_stable_ties():
    rows = [
        row('outline', 'newer-b', 0, 0.5, '2026-08-27T00:00:00', ['semantic']),
        row('outline', 'newer-a', 0, 0.5, '2026-08-27T00:00:00', ['semantic']),
        row('outline', 'older', 0, 0.5, '2026-08-26T00:00:00', ['semantic']),
        row('outline', 'newer-a', 1, 0.4, '2026-08-27T00:00:00', ['trigram']),
        row('outline', 'newer-a', 2, 0.3, '2026-08-27T00:00:00', ['fulltext']),
        row('outline', 'newer-a', 3, 0.2, '2026-08-27T00:00:00', ['semantic']),
    ]

    results = aggregate_chunk_matches(rows, limit=2, snippets_per_object=3)

    assert [item.source_object_id for item in results] == ['newer-a', 'newer-b']
    assert [match.chunk_no for match in results[0].matches] == [0, 1, 2]
    assert results[0].matched_by == ['semantic', 'trigram', 'fulltext']
