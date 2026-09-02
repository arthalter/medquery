from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InstructionDocument:
    """由药品注册表定位到的本地说明书正文及来源身份。"""

    document_id: str
    drug_name: str
    document_path: Path
    source_id: str


@dataclass(frozen=True, slots=True)
class InstructionSection:
    """从 TXT 中解析出的单个原始章节。"""

    heading: str
    text: str


@dataclass(frozen=True, slots=True)
class ChunkPiece:
    """切片正文；overlap 不计入 body 的字符额度。"""

    body: str
    overlap: str

    @property
    def text(self) -> str:
        if not self.overlap:
            return self.body
        return f"{self.overlap}\n{self.body}"


@dataclass(frozen=True, slots=True)
class InstructionChunk:
    chunk_id: str
    document_id: str
    drug_name: str
    section: str
    chunk_index: int
    text: str
    source_id: str

    @property
    def embedding_text(self) -> str:
        return f"药品：{self.drug_name}\n章节：{self.section}\n{self.text}"


@dataclass(frozen=True, slots=True)
class EmbeddedInstructionChunk:
    chunk: InstructionChunk
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class DenseCandidate:
    chunk_id: str
    document_id: str
    drug_name: str
    section: str
    chunk_index: int
    text: str
    source_id: str
    dense_score: float

    @property
    def rerank_text(self) -> str:
        return f"章节：{self.section}\n{self.text}"


@dataclass(frozen=True, slots=True)
class Evidence:
    """一次检索 Tool 调用产生的原文证据。"""

    chunk_id: str
    document_id: str
    drug_name: str
    section: str
    chunk_index: int
    text: str
    source_id: str
    rerank_score: float


@dataclass(frozen=True, slots=True)
class IngestReport:
    document_count: int
    chunk_count: int
    collection_name: str
