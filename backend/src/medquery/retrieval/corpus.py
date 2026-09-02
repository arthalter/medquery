from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from medquery.retrieval.models import InstructionDocument, InstructionSection


SECTION_HEADING = re.compile(r"^【(?P<heading>[^】]+)】\s*$", re.MULTILINE)


def _required_string(value: dict[str, Any], key: str, context: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{context} 缺少 {key}")
    return result.strip()


def _resolve_artifact_path(
    value: str,
    *,
    data_dir: Path,
    registry_path: Path,
) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.joinpath(*path.parts[1:])
    return registry_path.parent / path


def _read_source_id(metadata_path: Path, drug_id: str) -> str:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source = metadata.get("source")
    if not isinstance(source, dict):
        raise ValueError(f"{drug_id} 的元数据缺少 source")
    content_sha256 = source.get("content_sha256")
    if isinstance(content_sha256, str) and content_sha256.strip():
        return content_sha256.strip()
    source_url = source.get("url")
    if isinstance(source_url, str) and source_url.strip():
        return source_url.strip()
    raise ValueError(f"{drug_id} 的元数据缺少来源标识")


def load_instruction_documents(
    data_dir: Path,
    registry_path: Path | None = None,
) -> list[InstructionDocument]:
    """严格以 drugs.json 为入口，不扫描 TXT 目录。"""

    resolved_registry = registry_path or data_dir / "processed" / "drugs.json"
    payload = json.loads(resolved_registry.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("不支持的药品注册表版本")
    raw_drugs = payload.get("drugs")
    if not isinstance(raw_drugs, list):
        raise ValueError("药品注册表缺少 drugs 数组")

    documents: list[InstructionDocument] = []
    seen_ids: set[str] = set()
    for raw in raw_drugs:
        if not isinstance(raw, dict):
            raise ValueError("药品注册表包含非对象条目")
        drug_id = _required_string(raw, "drug_id", "药品条目")
        if drug_id in seen_ids:
            raise ValueError(f"药品注册表存在重复 drug_id：{drug_id}")
        seen_ids.add(drug_id)

        document_path = _resolve_artifact_path(
            _required_string(raw, "document_path", drug_id),
            data_dir=data_dir,
            registry_path=resolved_registry,
        )
        metadata_path = _resolve_artifact_path(
            _required_string(raw, "metadata_path", drug_id),
            data_dir=data_dir,
            registry_path=resolved_registry,
        )
        if not document_path.is_file():
            raise FileNotFoundError(f"说明书正文不存在：{document_path}")
        if not metadata_path.is_file():
            raise FileNotFoundError(f"说明书元数据不存在：{metadata_path}")

        documents.append(
            InstructionDocument(
                document_id=drug_id,
                drug_name=_required_string(raw, "drug_name", drug_id),
                document_path=document_path,
                source_id=_read_source_id(metadata_path, drug_id),
            )
        )
    return documents


def parse_instruction_sections(document_text: str) -> list[InstructionSection]:
    matches = list(SECTION_HEADING.finditer(document_text))
    if not matches:
        text = document_text.strip()
        return [InstructionSection(heading="正文", text=text)] if text else []

    sections: list[InstructionSection] = []
    for index, matched in enumerate(matches):
        body_start = matched.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else None
        body = document_text[body_start:body_end].strip()
        if body:
            sections.append(
                InstructionSection(
                    heading=matched.group("heading").strip(),
                    text=body,
                )
            )
    return sections
