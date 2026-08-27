import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.internal.db import get_async_session
from open_webui.mailuo.errors import (
    MailuoConfigurationError,
    MailuoDatabaseError,
    MailuoEmbeddingError,
    MailuoForbiddenError,
    MailuoSearchError,
)
from open_webui.mailuo.knowledge import list_accessible_mailuo_knowledges
from open_webui.mailuo.schemas import (
    MailuoFacetRequest,
    MailuoFacetResponse,
    MailuoKnowledge,
    MailuoSearchRequest,
    MailuoSearchResponse,
)
from open_webui.mailuo.service import MailuoSearchService
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter(prefix='/mailuo')
service = MailuoSearchService()


def _request_id(request: Request) -> str:
    return request.headers.get('x-request-id') or str(uuid.uuid4())


def _http_error(request: Request, exc: Exception) -> HTTPException:
    request_id = _request_id(request)
    log.warning(
        'mailuo_api_error request_id=%s error_class=%s',
        request_id,
        type(exc).__name__,
    )
    if isinstance(exc, MailuoForbiddenError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'message': 'Knowledge is not accessible', 'request_id': request_id},
        )
    if isinstance(exc, MailuoConfigurationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'message': 'Knowledge is not Mailuo-compatible', 'request_id': request_id},
        )
    if isinstance(exc, MailuoEmbeddingError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={'message': 'Embedding service is temporarily unavailable', 'request_id': request_id},
        )
    if isinstance(exc, (MailuoDatabaseError, MailuoSearchError)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={'message': 'Mailuo search is temporarily unavailable', 'request_id': request_id},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={'message': 'Mailuo search failed', 'request_id': request_id},
    )


@router.get('/knowledges', response_model=list[MailuoKnowledge])
async def get_mailuo_knowledges(
    user=Depends(get_verified_user),
    db=Depends(get_async_session),
):
    return await list_accessible_mailuo_knowledges(user, db=db)


@router.post('/facets', response_model=MailuoFacetResponse)
async def get_mailuo_facets(
    request: Request,
    form: MailuoFacetRequest,
    user=Depends(get_verified_user),
    db=Depends(get_async_session),
):
    try:
        return await service.facets(form.knowledge_ids, user, db=db)
    except Exception as exc:
        raise _http_error(request, exc) from None


@router.post('/search', response_model=MailuoSearchResponse)
async def search_mailuo(
    request: Request,
    form: MailuoSearchRequest,
    user=Depends(get_verified_user),
    db=Depends(get_async_session),
):
    try:
        return await service.search(request, form, user, db=db)
    except Exception as exc:
        raise _http_error(request, exc) from None
