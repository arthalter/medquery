import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from medquery.agent import DrugQuestionAgent
from medquery.config import Settings
from medquery.drugs import DrugRegistry
from medquery.recognition import DrugRecognizer
from medquery.session import InMemorySessionStore


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    resume: bool = False


class DrugConfirmationRequest(BaseModel):
    drug_id: str = Field(min_length=1)
    accepted: bool


def create_api_router(
    settings: Settings,
    sessions: InMemorySessionStore,
    registry: DrugRegistry,
    recognizer: DrugRecognizer,
    question_agent: DrugQuestionAgent,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/sessions")
    async def create_session() -> dict[str, str]:
        state = sessions.create()
        return {"session_id": state.session_id}

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, object]:
        state = sessions.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        confirmed = (
            registry.get(state.confirmed_drug_id)
            if state.confirmed_drug_id
            else None
        )
        pending_candidates = [
            candidate.to_client_dict()
            for candidate_id in state.pending_drug_ids
            if (candidate := registry.get(candidate_id)) is not None
        ]
        return {
            "session_id": state.session_id,
            "confirmed_drug": (
                confirmed.to_client_dict() if confirmed else None
            ),
            "pending_candidates": pending_candidates,
            "turns": [
                {
                    "question": turn.question,
                    "answer": turn.answer,
                    "evidence": turn.evidence,
                }
                for turn in state.turns
            ],
        }

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
                "question": state.pending_question,
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
    async def chat_stream(
        chat_request: ChatRequest,
        request: Request,
    ) -> StreamingResponse:
        state = (
            sessions.get(chat_request.session_id)
            if chat_request.session_id
            else None
        )
        if chat_request.session_id and state is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        if state is None:
            state = sessions.create()

        current_question = (
            state.pending_question
            if chat_request.resume and state.pending_question
            else chat_request.message
        )
        if not chat_request.resume:
            state.begin_question(current_question)

        async def events() -> AsyncIterator[str]:
            yield _sse("session", {"session_id": state.session_id})
            if state.confirmed_drug_id:
                drug = registry.get(state.confirmed_drug_id)
                if not chat_request.resume:
                    detected = await recognizer.recognize(
                        state,
                        current_question,
                        settings.session_history_rounds,
                    )
                    switch_candidates = [
                        candidate
                        for candidate in detected
                        if candidate.drug_id != state.confirmed_drug_id
                    ]
                    if switch_candidates:
                        state.clear_confirmed_drug()
                        state.set_pending(
                            [candidate.drug_id for candidate in switch_candidates]
                        )
                        state.add_message("assistant", "请确认要切换的药品。")
                        yield _sse(
                            "drug_confirmation_required",
                            {
                                "candidates": [
                                    candidate.to_client_dict()
                                    for candidate in switch_candidates
                                ]
                            },
                        )
                        return
                yield _sse(
                    "drug_confirmed",
                    {"drug": drug.to_client_dict() if drug else None},
                )
                if drug is None:
                    raise RuntimeError("确认药品不在药品注册表中")
                outcome = await question_agent.answer(
                    state,
                    current_question,
                    drug.drug_name,
                    request.app.state.milvus,
                )
                state.complete_answer(
                    outcome.answer,
                    list(outcome.evidence),
                )
                for delta in _answer_chunks(outcome.answer):
                    yield _sse("answer_delta", {"delta": delta})
                yield _sse(
                    "evidence",
                    {"evidence": list(outcome.evidence)},
                )
                yield _sse("done", {})
                return

            candidates = await recognizer.recognize(
                state,
                current_question,
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


def _answer_chunks(answer: str, chunk_size: int = 24) -> list[str]:
    return [
        answer[index : index + chunk_size]
        for index in range(0, len(answer), chunk_size)
    ]
