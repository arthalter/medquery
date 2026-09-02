from __future__ import annotations

from typing import ClassVar

from medquery.retrieval.service import InstructionRetrievalService


class DrugInstructionSearchTool:
    """后续 Agent 唯一知识库 Tool 的框架无关接口。"""

    name: ClassVar[str] = "search_drug_instructions"
    description: ClassVar[str] = (
        "从用户已确认药品的中文说明书中检索与当前问题相关的原文证据。"
    )

    def __init__(
        self,
        service: InstructionRetrievalService,
        confirmed_drug_name: str,
    ) -> None:
        self._service = service
        self._confirmed_drug_name = confirmed_drug_name

    def invoke(self, atomic_question: str) -> list[dict[str, str]]:
        evidence = self._service.search(
            drug_name=self._confirmed_drug_name,
            atomic_question=atomic_question,
        )
        return [{"text": item.text} for item in evidence]
