import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from medquery.session import InMemorySessionStore


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


def create_api_router(
    sessions: InMemorySessionStore,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/sessions")
    async def create_session() -> dict[str, str]:
        state = sessions.create()
        return {"session_id": state.session_id}

    @router.post("/chat/stream")
    async def chat_stream(request: ChatRequest) -> StreamingResponse:
        state = sessions.get(request.session_id) if request.session_id else None
        if request.session_id and state is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        if state is None:
            state = sessions.create()

        async def events() -> AsyncIterator[str]:
            yield _sse("session", {"session_id": state.session_id})
            yield _sse(
                "ready",
                {
                    "message": request.message,
                    "status": "agent_pending",
                },
            )

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return router


def _sse(event: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"
