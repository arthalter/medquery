from __future__ import annotations

from dataclasses import dataclass

from pymilvus import MilvusClient

from medquery.config import Settings
from medquery.grok import GrokChatClient
from medquery.retrieval.service import InstructionRetrievalService
from medquery.retrieval.tool import DrugInstructionSearchTool
from medquery.rewrite import QuestionRewriter
from medquery.session import SessionState


AGENT_PROMPT = """你是药品说明书问答 Agent，只能处理已确认药品。
每一轮必须在两个动作中自主选择一个：
1. 需要继续查说明书时，返回 {"action":"search","atomic_question":"..."}。
2. 已经可以回答时，返回 {"action":"final","answer":"..."}。
一次只选择一个动作。检索结果会在下一轮作为 steps 返回给你。
最终答案使用简洁中文，只依据 steps 中的证据；页面会单独展示证据正文，不要生成证据卡。
只输出 JSON，不要输出额外文字。"""


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    answer: str
    evidence: tuple[str, ...]


class DrugQuestionAgent:
    """使用普通 JSON 对话驱动单工具串行 Agent 循环。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = GrokChatClient(settings)
        self._rewriter = QuestionRewriter(self._client)

    async def answer(
        self,
        state: SessionState,
        current_question: str,
        confirmed_drug_name: str,
        milvus: MilvusClient,
    ) -> AgentOutcome:
        rewrite = await self._rewriter.rewrite(
            state,
            current_question,
            confirmed_drug_name,
            self._settings.session_history_rounds,
        )
        retrieval = InstructionRetrievalService(self._settings, milvus)
        tool = DrugInstructionSearchTool(retrieval, confirmed_drug_name)
        evidence: list[str] = []
        steps: list[dict[str, object]] = []

        while True:
            decision = await self._client.complete_json(
                AGENT_PROMPT,
                {
                    "confirmed_drug_name": confirmed_drug_name,
                    "original_question": current_question,
                    "rewritten_atomic_questions": list(
                        rewrite.atomic_questions
                    ),
                    "steps": steps,
                },
            )
            action = str(decision.get("action", ""))
            if action == "search":
                atomic_question = str(
                    decision.get("atomic_question", "")
                ).strip()
                if not atomic_question:
                    raise RuntimeError("Agent 的 search 动作缺少原子问题")
                hits = tool.invoke(atomic_question)
                texts = [str(item["text"]) for item in hits]
                evidence.extend(texts)
                steps.append(
                    {
                        "action": "search",
                        "atomic_question": atomic_question,
                        "evidence": texts,
                    }
                )
                continue

            if action == "final":
                answer = str(decision.get("answer", "")).strip()
                if not answer:
                    raise RuntimeError("Agent 的 final 动作缺少答案")
                return AgentOutcome(answer=answer, evidence=tuple(evidence))

            raise RuntimeError(f"Agent 返回了未知动作：{action}")
