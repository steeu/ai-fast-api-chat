import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.deps import ChatServiceDep
from app.core.security import get_current_user
from app.schemas.chat import ChatRequest, UsageReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user)])


@router.post("/stream", response_class=EventSourceResponse)
async def stream_chat(
    request: ChatRequest, service: ChatServiceDep
) -> AsyncIterable[ServerSentEvent]:
    """Stream the answer as SSE: `token`*, optional `usage`, then `done` or `error`."""
    try:
        async for item in service.stream_reply(request.messages):
            if isinstance(item, UsageReport):
                yield ServerSentEvent(data=item.model_dump(), event="usage")
            else:
                yield ServerSentEvent(data=item, event="token")
    except ValueError as exc:
        yield ServerSentEvent(data=str(exc), event="error")
        return
    except Exception:
        logger.exception("Chat stream failed")
        yield ServerSentEvent(data="The AI service is currently unavailable.", event="error")
        return
    yield ServerSentEvent(data="", event="done")
