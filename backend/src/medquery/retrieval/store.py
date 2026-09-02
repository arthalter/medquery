from __future__ import annotations

from collections.abc import Sequence

from pymilvus import DataType, MilvusClient

from medquery.config import Settings
from medquery.retrieval.models import DenseCandidate, EmbeddedInstructionChunk


INSERT_BATCH_SIZE = 200


def _milvus_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


class MilvusInstructionStore:
    """说明书 Dense 向量的 Milvus Lite 存取边界。"""

    def __init__(self, client: MilvusClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _create_collection(self) -> None:
        schema = self._client.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(
            field_name="chunk_id",
            datatype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=256,
        )
        schema.add_field(
            field_name="document_id",
            datatype=DataType.VARCHAR,
            max_length=256,
        )
        schema.add_field(
            field_name="drug_name",
            datatype=DataType.VARCHAR,
            max_length=256,
        )
        schema.add_field(
            field_name="section",
            datatype=DataType.VARCHAR,
            max_length=256,
        )
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=65535,
        )
        schema.add_field(
            field_name="source_id",
            datatype=DataType.VARCHAR,
            max_length=2048,
        )
        schema.add_field(
            field_name="embedding",
            datatype=DataType.FLOAT_VECTOR,
            dim=self._settings.bailian_embedding_dimensions,
        )

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_name="embedding_flat",
            index_type="FLAT",
            metric_type="COSINE",
            params={},
        )
        self._client.create_collection(
            collection_name=self._settings.milvus_collection,
            schema=schema,
            index_params=index_params,
        )

    def rebuild(self, chunks: Sequence[EmbeddedInstructionChunk]) -> None:
        if not chunks:
            raise ValueError("没有可写入 Milvus 的说明书切片")

        collection_name = self._settings.milvus_collection
        if self._client.has_collection(collection_name=collection_name):
            self._client.drop_collection(collection_name=collection_name)
        self._create_collection()

        rows = [
            {
                "chunk_id": item.chunk.chunk_id,
                "document_id": item.chunk.document_id,
                "drug_name": item.chunk.drug_name,
                "section": item.chunk.section,
                "chunk_index": item.chunk.chunk_index,
                "text": item.chunk.text,
                "source_id": item.chunk.source_id,
                "embedding": list(item.embedding),
            }
            for item in chunks
        ]
        for start in range(0, len(rows), INSERT_BATCH_SIZE):
            self._client.insert(
                collection_name=collection_name,
                data=rows[start : start + INSERT_BATCH_SIZE],
            )
        self._client.load_collection(collection_name=collection_name)

    def search(
        self,
        *,
        drug_name: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> list[DenseCandidate]:
        collection_name = self._settings.milvus_collection
        if not self._client.has_collection(collection_name=collection_name):
            raise RuntimeError("说明书向量库尚未入库，请先运行 medquery ingest")
        self._client.load_collection(collection_name=collection_name)
        results = self._client.search(
            collection_name=collection_name,
            anns_field="embedding",
            data=[list(query_embedding)],
            filter=f"drug_name == {_milvus_string_literal(drug_name)}",
            limit=limit,
            output_fields=[
                "document_id",
                "drug_name",
                "section",
                "chunk_index",
                "text",
                "source_id",
            ],
            search_params={"metric_type": "COSINE", "params": {}},
        )
        hits = results[0] if results else []
        candidates: list[DenseCandidate] = []
        for hit in hits:
            entity = hit.get("entity") or {}
            candidates.append(
                DenseCandidate(
                    chunk_id=str(hit.get("id", "")),
                    document_id=str(entity.get("document_id", "")),
                    drug_name=str(entity.get("drug_name", "")),
                    section=str(entity.get("section", "")),
                    chunk_index=int(entity.get("chunk_index", 0)),
                    text=str(entity.get("text", "")),
                    source_id=str(entity.get("source_id", "")),
                    dense_score=float(hit.get("distance", 0.0)),
                )
            )
        return candidates
