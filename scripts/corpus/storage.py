from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from .extract import build_document_text
from .schema import CollectionManifest, DrugCandidate, DrugRecord, SourceCandidate


def save_raw_page(
    raw_dir: Path,
    candidate: DrugCandidate,
    source: SourceCandidate,
    payload: bytes,
) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{candidate.drug_id}.priority-{source.priority}.html"
    path.write_bytes(payload)
    return path


def save_record(
    processed_dir: Path,
    record: DrugRecord,
    raw_path: Path,
) -> dict[str, Any]:
    documents_dir = processed_dir / "documents"
    metadata_dir = processed_dir / "metadata"
    documents_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    document_path = documents_dir / record.document_filename
    metadata_path = metadata_dir / record.metadata_filename
    document_path.write_text(build_document_text(record.sections), encoding="utf-8")

    identity = {
        "drug_id": record.drug_id,
        "drug_name": record.drug_name,
        "aliases": list(record.aliases),
        "dosage_form": record.dosage_form,
        "specification": record.specification,
        "manufacturer": record.manufacturer,
        "approval_number": record.approval_number,
    }
    metadata = {
        "schema_version": 1,
        **identity,
        "source": {
            "site": record.source_site,
            "url": record.source_url,
            "fetched_at": record.fetched_at,
            "raw_path": raw_path.as_posix(),
            "content_sha256": record.content_sha256,
        },
        "available_sections": sorted(record.sections),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        **identity,
        "document_path": document_path.as_posix(),
        "metadata_path": metadata_path.as_posix(),
    }


def write_outputs(
    processed_dir: Path,
    manifest: CollectionManifest,
    registry: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    started_at: str,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    registry_payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drugs": registry,
    }
    (processed_dir / "drugs.json").write_text(
        json.dumps(registry_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "minimum_required": manifest.minimum_required,
        "accepted_count": len(registry),
        "rejected_count": len(rejected),
        "accepted_drug_ids": [item["drug_id"] for item in registry],
        "rejected": rejected,
    }
    (processed_dir / "collection-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
