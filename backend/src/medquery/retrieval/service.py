from __future__ import annotations

from pymilvus import MilvusClient

from medquery.config import Settings
from medquery.retrieval.bailian import BailianClient
from medquery.retrieval.chunking import chunk_section
from medquery.retrieval.corpus import (
    load_instruction_documents,
    parse_instruction_sections,
)
from medquery.retrieval.models import (
    EmbeddedInstructionChunk,
    Evidence,
    IngestReport,
    InstructionChunk,
)
from medquery.retrieval.store import MilvusInstructionStore


class InstructionIngestor:
    """组合 TXT、切片、Embedding 与 Milvus，供离线 CLI 单次调用。"""

    def __init__(self, settings: Settings, milvus: MilvusClient) -> None:
        self._settings = settings
        self._bailian = BailianClient(settings)
        self._store = MilvusInstructionStore(milvus, settings)

    def _load_chunks(self) -> tuple[int, list[InstructionChunk]]:
        documents = load_instruction_documents(self._settings.data_dir)
        chunks: list[InstructionChunk] = []
        for document in documents:
            document_text = document.document_path.read_text(encoding="utf-8")
            chunk_index = 0
            for section in parse_instruction_sections(document_text):
                pieces = chunk_section(
                    section.text,
                    char_limit=self._settings.chunk_char_limit,
                    overlap_last_sentence=self._settings.chunk_overlap_last_sentence,
                )
                for piece in pieces:
                    chunks.append(
                        InstructionChunk(
                            chunk_id=f"{document.document_id}:{chunk_index:05d}",
                            document_id=document.document_id,
                            drug_name=document.drug_name,
                            section=section.heading,
                            chunk_index=chunk_index,
                            text=piece.text,
                            source_id=document.source_id,
                        )
                    )
                    chunk_index += 1
        return len(documents), chunks

    def ingest(self) -> IngestReport:
        document_count, chunks = self._load_chunks()
        if not chunks:
            raise ValueError("药品注册表没有产生任何说明书切片")

        embeddings = self._bailian.embed_documents(
            [chunk.embedding_text for chunk in chunks]
        )
        if len(embeddings) != len(chunks):
            raise RuntimeError("Embedding 数量与说明书切片数量不一致")

        embedded_chunks = [
            EmbeddedInstructionChunk(chunk=chunk, embedding=embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._store.rebuild(embedded_chunks)
        return IngestReport(
            document_count=document_count,
            chunk_count=len(chunks),
            collection_name=self._settings.milvus_collection,
        )


class InstructionRetrievalService:
    """按确认药名执行 Dense Top 10，再返回 Rerank Top 3。"""

    def __init__(self, settings: Settings, milvus: MilvusClient) -> None:
        self._settings = settings
        self._bailian = BailianClient(settings)
        self._store = MilvusInstructionStore(milvus, settings)

    def search(self, drug_name: str, atomic_question: str) -> list[Evidence]:
        query = f"药品：{drug_name}\n问题：{atomic_question}"
        query_embedding = self._bailian.embed_query(query)
        candidates = self._store.search(
            drug_name=drug_name,
            query_embedding=query_embedding,
            limit=self._settings.dense_top_k,
        )
        if not candidates:
            return []

        reranked = self._bailian.rerank(
            query=query,
            documents=[candidate.rerank_text for candidate in candidates],
        )
        evidence: list[Evidence] = []
        for result in reranked:
            if result.score < self._settings.rerank_min_score:
                continue
            candidate = candidates[result.index]
            evidence.append(
                Evidence(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    drug_name=candidate.drug_name,
                    section=candidate.section,
                    chunk_index=candidate.chunk_index,
                    text=candidate.text,
                    source_id=candidate.source_id,
                    rerank_score=result.score,
                )
            )
        return evidence
