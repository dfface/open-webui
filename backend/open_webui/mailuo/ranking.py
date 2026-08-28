from collections import defaultdict

from open_webui.mailuo.schemas import (
    MailuoChunkMatch,
    MailuoObjectResult,
    MailuoSnippet,
    SearchSort,
)


def _merge_ordered(values: list[list[str]]) -> list[str]:
    return list(dict.fromkeys(value for group in values for value in group))


def aggregate_chunk_matches(
    rows: list[MailuoChunkMatch],
    limit: int = 20,
    snippets_per_object: int = 3,
    sort: SearchSort = SearchSort.RELEVANCE,
) -> list[MailuoObjectResult]:
    grouped: dict[tuple[str, str], list[MailuoChunkMatch]] = defaultdict(list)
    for row in rows:
        grouped[(row.source, row.source_object_id)].append(row)

    results = []
    for matches in grouped.values():
        matches.sort(key=lambda match: (-match.score, match.chunk_no, match.knowledge_id))
        best = matches[0]
        results.append(
            MailuoObjectResult(
                knowledge_ids=list(dict.fromkeys(match.knowledge_id for match in matches)),
                source=best.source,
                source_object_id=best.source_object_id,
                title=best.title,
                source_url=best.source_url,
                source_updated_at=max(match.source_updated_at for match in matches),
                metadata=best.metadata,
                matched_by=_merge_ordered([match.matched_by for match in matches]),
                matches=[
                    MailuoSnippet(
                        chunk_no=match.chunk_no,
                        content=match.content,
                        matched_by=match.matched_by,
                    )
                    for match in matches[:snippets_per_object]
                ],
                score=best.score,
            )
        )

    if sort == SearchSort.UPDATED_DESC:
        results.sort(
            key=lambda result: (
                -result.source_updated_at.timestamp(),
                -result.score,
                result.source,
                result.source_object_id,
            )
        )
    elif sort == SearchSort.UPDATED_ASC:
        results.sort(
            key=lambda result: (
                result.source_updated_at.timestamp(),
                -result.score,
                result.source,
                result.source_object_id,
            )
        )
    else:
        results.sort(
            key=lambda result: (
                -result.score,
                -result.source_updated_at.timestamp(),
                result.source,
                result.source_object_id,
            )
        )
    return results[:limit]
