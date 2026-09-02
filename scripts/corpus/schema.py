from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class SourceCandidate:
    """同一药品的一条候选详情页，按 priority 从小到大尝试。"""

    site: str
    url: str
    priority: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SourceCandidate:
        return cls(
            site=str(value["site"]).strip(),
            url=str(value["url"]).strip(),
            priority=int(value.get("priority", 1)),
        )


@dataclass(frozen=True)
class DrugCandidate:
    """药品的稳定身份以及按优先级排列的候选来源。"""

    drug_id: str
    expected_drug_name: str
    aliases: tuple[str, ...]
    sources: tuple[SourceCandidate, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DrugCandidate:
        sources = tuple(
            sorted(
                (SourceCandidate.from_dict(item) for item in value["sources"]),
                key=lambda item: item.priority,
            )
        )
        if not sources:
            raise ValueError(f"{value['drug_id']} 没有候选来源")
        return cls(
            drug_id=str(value["drug_id"]).strip(),
            expected_drug_name=str(value["expected_drug_name"]).strip(),
            aliases=tuple(str(item).strip() for item in value.get("aliases", [])),
            sources=sources,
        )


@dataclass(frozen=True)
class CollectionManifest:
    """可提交到仓库的来源清单；不包含抓取后的说明书全文。"""

    version: int
    minimum_required: int
    drugs: tuple[DrugCandidate, ...]

    @classmethod
    def load(cls, path: Path) -> CollectionManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        drugs = tuple(DrugCandidate.from_dict(item) for item in raw["drugs"])
        manifest = cls(
            version=int(raw["version"]),
            minimum_required=int(raw.get("minimum_required", 20)),
            drugs=drugs,
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.version != 1:
            raise ValueError(f"不支持的来源清单版本：{self.version}")
        if self.minimum_required < 20:
            raise ValueError("minimum_required 不能少于 20")
        if len(self.drugs) < self.minimum_required:
            raise ValueError(
                f"来源清单只有 {len(self.drugs)} 种药，少于要求的 "
                f"{self.minimum_required} 种"
            )

        ids = [item.drug_id for item in self.drugs]
        if len(ids) != len(set(ids)):
            raise ValueError("来源清单存在重复 drug_id")
        if any(not item.isascii() for item in ids):
            raise ValueError("drug_id 必须使用 ASCII 字符")
        if any(not item.aliases for item in self.drugs):
            raise ValueError("每个药品至少需要一个识别别名")


@dataclass(frozen=True)
class ExtractedInstruction:
    """页面提取结果；此时尚未通过质量门槛。"""

    page_title: str
    sections: dict[str, str]


@dataclass(frozen=True)
class DrugRecord:
    """通过质量门槛后写入本地语料的标准记录。"""

    drug_id: str
    drug_name: str
    aliases: tuple[str, ...]
    dosage_form: str
    specification: str
    manufacturer: str
    approval_number: str
    sections: dict[str, str]
    source_site: str
    source_url: str
    fetched_at: str
    content_sha256: str

    @property
    def document_filename(self) -> str:
        return f"{self.drug_id}.txt"

    @property
    def metadata_filename(self) -> str:
        return f"{self.drug_id}.json"
