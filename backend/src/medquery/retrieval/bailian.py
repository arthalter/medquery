from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.request import Request, urlopen
import json

from medquery.config import Settings


EMBEDDING_BATCH_SIZE = 10


@dataclass(frozen=True, slots=True)
class RerankResult:
    index: int
    score: float


class BailianClient:
    """使用 Python 标准库调用百炼北京地域原生 HTTP 接口。"""

    def __init__(self, settings: Settings) -> None:
        if settings.bailian_region != "cn-beijing":
            raise ValueError("当前 Demo 只配置百炼 cn-beijing 地域")
        workspace_id = settings.bailian_workspace_id.strip()
        api_key = settings.bailian_api_key.get_secret_value().strip()
        if not workspace_id:
            raise ValueError("BAILIAN_WORKSPACE_ID 尚未配置")
        if not api_key:
            raise ValueError("BAILIAN_API_KEY 尚未配置")

        self._settings = settings
        self._api_key = api_key
        self._host = f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com"

    def _request_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self._host}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict):
            raise RuntimeError("百炼返回了非对象响应")
        code = result.get("code")
        if code:
            raise RuntimeError(
                f"百炼调用失败：{code} {result.get('message', '')}".strip()
            )
        return result

    def _embed(
        self,
        texts: Sequence[str],
        text_type: Literal["document", "query"],
    ) -> list[tuple[float, ...]]:
        if not texts:
            return []

        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = list(texts[start : start + EMBEDDING_BATCH_SIZE])
            response = self._request_json(
                "/api/v1/services/embeddings/text-embedding/text-embedding",
                {
                    "model": self._settings.bailian_embedding_model,
                    "input": {"texts": batch},
                    "parameters": {
                        "text_type": text_type,
                        "dimension": self._settings.bailian_embedding_dimensions,
                        "output_type": "dense",
                    },
                },
            )
            output = response.get("output")
            embeddings = output.get("embeddings") if isinstance(output, dict) else None
            if not isinstance(embeddings, list):
                raise RuntimeError("百炼 Embedding 响应缺少 output.embeddings")

            ordered: list[tuple[float, ...] | None] = [None] * len(batch)
            for item in embeddings:
                if not isinstance(item, dict):
                    raise RuntimeError("百炼 Embedding 响应包含无效条目")
                text_index = item.get("text_index")
                embedding = item.get("embedding")
                if not isinstance(text_index, int) or not isinstance(embedding, list):
                    raise RuntimeError("百炼 Embedding 条目缺少索引或稠密向量")
                if text_index < 0 or text_index >= len(batch):
                    raise RuntimeError("百炼 Embedding 返回了越界索引")
                vector = tuple(float(value) for value in embedding)
                if len(vector) != self._settings.bailian_embedding_dimensions:
                    raise RuntimeError(
                        "百炼 Embedding 向量维度与配置不一致："
                        f"期望 {self._settings.bailian_embedding_dimensions}，"
                        f"实际 {len(vector)}"
                    )
                ordered[text_index] = vector

            if any(vector is None for vector in ordered):
                raise RuntimeError("百炼 Embedding 返回数量与输入不一致")
            vectors.extend(vector for vector in ordered if vector is not None)
        return vectors

    def embed_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> tuple[float, ...]:
        vectors = self._embed([text], "query")
        return vectors[0]

    def rerank(
        self,
        query: str,
        documents: Sequence[str],
    ) -> list[RerankResult]:
        if not documents:
            return []
        response = self._request_json(
            "/compatible-api/v1/reranks",
            {
                "model": self._settings.bailian_rerank_model,
                "query": query,
                "documents": list(documents),
                "top_n": self._settings.rerank_top_k,
            },
        )
        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise RuntimeError("百炼 Rerank 响应缺少 results")

        results: list[RerankResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                raise RuntimeError("百炼 Rerank 响应包含无效条目")
            index = item.get("index")
            score = item.get("relevance_score")
            if not isinstance(index, int) or not isinstance(score, int | float):
                raise RuntimeError("百炼 Rerank 条目缺少索引或分数")
            if index < 0 or index >= len(documents):
                raise RuntimeError("百炼 Rerank 返回了越界索引")
            results.append(RerankResult(index=index, score=float(score)))
        return results
