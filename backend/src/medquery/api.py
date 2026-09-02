import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from medquery.config import Settings
from medquery.drugs import DrugRegistry
from medquery.recognition import DrugRecognizer
from medquery.session import InMemorySessionStore


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class DrugConfirmationRequest(BaseModel):
    drug_id: str = Field(min_length=1)
    accepted: bool


def create_api_router(
    settings: Settings,
    sessions: InMemorySessionStore,
    registry: DrugRegistry,
    recognizer: DrugRecognizer,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/sessions")
    async def create_session() -> dict[str, str]:
        state = sessions.create()
        return {"session_id": state.session_id}

    @router.post("/sessions/{session_id}/drug-confirmation")
    async def confirm_drug(
        session_id: str,
        request: DrugConfirmationRequest,
    ) -> dict[str, object]:
        state = sessions.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        if request.drug_id not in state.pending_drug_ids:
            raise HTTPException(status_code=409, detail="该药品不是待确认候选")

        drug = registry.get(request.drug_id)
        if drug is None:
            raise HTTPException(status_code=404, detail="药品不存在")
        if request.accepted:
            state.confirm_drug(drug.drug_id, drug.drug_name)
            state.add_message("assistant", f"已确认药品：{drug.drug_name}")
            return {
                "status": "confirmed",
                "drug": drug.to_client_dict(),
            }

        state.reject_drug(drug.drug_id)
        state.add_message("assistant", f"已排除候选：{drug.drug_name}")
        remaining = [
            candidate.to_client_dict()
            for candidate_id in state.pending_drug_ids
            if (candidate := registry.get(candidate_id)) is not None
        ]
        return {
            "status": "rejected",
            "message": (
                "请选择其他候选。"
                if remaining
                else "请补充或修正药品名称后继续提问。"
            ),
            "candidates": remaining,
        }

    @router.post("/chat/stream")
    async def chat_stream(request: ChatRequest) -> StreamingResponse:
        state = sessions.get(request.session_id) if request.session_id else None
        if request.session_id and state is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        if state is None:
            state = sessions.create()
        state.add_message("user", request.message)

        async def events() -> AsyncIterator[str]:
            yield _sse("session", {"session_id": state.session_id})
            if state.confirmed_drug_id:
                drug = registry.get(state.confirmed_drug_id)
                yield _sse(
                    "drug_confirmed",
                    {"drug": drug.to_client_dict() if drug else None},
                )
                return

            candidates = await recognizer.recognize(
                state,
                request.message,
                settings.session_history_rounds,
            )
            if not candidates:
                state.add_message("assistant", "请补充要查询的药品名称。")
                yield _sse(
                    "drug_clarification_required",
                    {"message": "请补充要查询的药品名称。"},
                )
                return

            state.set_pending([drug.drug_id for drug in candidates])
            state.add_message("assistant", "请确认要查询的药品。")
            yield _sse(
                "drug_confirmation_required",
                {"candidates": [drug.to_client_dict() for drug in candidates]},
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
