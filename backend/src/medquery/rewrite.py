from __future__ import annotations

from dataclasses import dataclass

from medquery.grok import GrokChatClient
from medquery.session import SessionMessage, SessionState


REWRITE_PROMPT = """你负责把当前药品说明书问题改写为便于知识库检索的原子问题。
结合确认药品、最近对话和当前问题消解代词与省略。
可以输出一个或多个原子问题，最多建议五个；不要回答问题，不要检索。
输出 JSON：{"atomic_questions":["..."]}。"""


@dataclass(frozen=True, slots=True)
class RewriteResult:
    atomic_questions: tuple[str, ...]


class QuestionRewriter:
    def __init__(self, client: GrokChatClient) -> None:
        self._client = client

    async def rewrite(
        self,
        state: SessionState,
        current_question: str,
        confirmed_drug_name: str,
        history_rounds: int,
    ) -> RewriteResult:
        recent_messages = state.recent_complete_turns(history_rounds)
        payload = {
            "confirmed_drug_name": confirmed_drug_name,
            "conversation": [
                _message_payload(message)
                for message in recent_messages
            ],
            "current_question": current_question,
        }
        response = await self._client.complete_json(REWRITE_PROMPT, payload)
        questions = tuple(
            str(item).strip()
            for item in response.get("atomic_questions", [])
            if str(item).strip()
        )
        return RewriteResult(atomic_questions=questions)


def _message_payload(message: SessionMessage) -> dict[str, str]:
    return {"role": message.role, "content": message.content}
