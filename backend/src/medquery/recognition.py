from __future__ import annotations

from medquery.drugs import DrugIdentity, DrugRegistry
from medquery.grok import GrokChatClient
from medquery.session import SessionMessage, SessionState


RECOGNITION_PROMPT = """你负责从受控药品目录中识别用户正在询问的药品。
只能返回目录中存在的 drug_id，不得创造新药品。
结合最近对话、当前消息和已拒绝候选判断，返回最可能的候选；即使只有一个候选也必须交给用户确认。
如果已有确认药品，而当前消息只是对它的追问且没有出现另一药品，返回空候选数组。
候选不明确时返回多个候选；没有合理候选时返回空数组。
输出 JSON：{"candidates":[{"drug_id":"...","reason":"..."}]}。
候选应尽量精简，最多建议三个。"""


class DrugRecognizer:
    def __init__(self, client: GrokChatClient, registry: DrugRegistry) -> None:
        self._client = client
        self._registry = registry

    async def recognize(
        self,
        state: SessionState,
        current_message: str,
        history_rounds: int,
    ) -> list[DrugIdentity]:
        recent_messages = state.recent_complete_turns(history_rounds)
        payload = {
            "conversation": [_message_payload(item) for item in recent_messages],
            "current_message": current_message,
            "confirmed_drug_id": state.confirmed_drug_id,
            "confirmed_drug_name": state.confirmed_drug_name,
            "rejected_drug_ids": list(state.rejected_drug_ids),
            "drug_catalog": self._registry.prompt_catalog(),
        }
        response = await self._client.complete_json(RECOGNITION_PROMPT, payload)
        candidates: list[DrugIdentity] = []
        for item in response.get("candidates", []):
            drug_id = str(item.get("drug_id", ""))
            if drug_id in state.rejected_drug_ids:
                continue
            drug = self._registry.get(drug_id)
            if drug and drug not in candidates:
                candidates.append(drug)
        return candidates


def _message_payload(message: SessionMessage) -> dict[str, str]:
    return {"role": message.role, "content": message.content}
