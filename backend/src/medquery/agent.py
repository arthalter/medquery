from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

from langchain.agents import create_agent
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pymilvus import MilvusClient

from medquery.config import Settings
from medquery.grok import GrokChatClient
from medquery.retrieval.service import InstructionRetrievalService
from medquery.rewrite import QuestionRewriter
from medquery.session import SessionState


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    answer: str
    evidence: tuple[str, ...]


class DrugQuestionAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rewriter = QuestionRewriter(GrokChatClient(settings))
        self._model = ChatOpenAI(
            model=settings.grok_model,
            base_url=settings.grok_base_url,
            api_key=settings.grok_api_key.get_secret_value(),
            use_responses_api=False,
            temperature=0,
            timeout=None,
            max_retries=0,
            model_kwargs={"parallel_tool_calls": False},
        )

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

        @tool("search_drug_instructions", response_format="content_and_artifact")
        def search_drug_instructions(
            atomic_question: str,
        ) -> tuple[str, dict[str, list[str]]]:
            """从已确认药品的说明书中检索与一个原子问题相关的原文。"""

            hits = retrieval.search(confirmed_drug_name, atomic_question)
            evidence = [item.text for item in hits]
            return (
                json.dumps({"evidence": evidence}, ensure_ascii=False),
                {"evidence": evidence},
            )

        atomic_questions = list(rewrite.atomic_questions)
        user_payload = {
            "confirmed_drug_name": confirmed_drug_name,
            "original_question": current_question,
            "rewritten_atomic_questions": atomic_questions,
        }
        agent = create_agent(
            model=self._model,
            tools=[search_drug_instructions],
            system_prompt=(
                "你是药品说明书问答助手。只使用已确认药品。"
                "你可以自主决定是否以及调用多少次唯一的说明书检索工具，"
                "所有工具调用必须串行。完成检索后生成一次简洁的中文答案。"
                "页面会单独展示工具证据，因此答案中不要编造证据卡。"
            ),
        )
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    }
                ]
            }
        )
        messages = result["messages"]
        final_message = next(
            message
            for message in reversed(messages)
            if isinstance(message, AIMessage) and not message.tool_calls
        )
        evidence: list[str] = []
        for message in messages:
            if isinstance(message, ToolMessage) and isinstance(
                message.artifact, dict
            ):
                values = message.artifact.get("evidence", [])
                if isinstance(values, list):
                    evidence.extend(str(item) for item in values)
        return AgentOutcome(
            answer=_message_text(final_message),
            evidence=tuple(evidence),
        )


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict)
        )
    return str(content)
