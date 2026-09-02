from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import sys
import time

from .extract import extract_instruction
from .http import DEFAULT_USER_AGENT, fetch_page
from .quality import (
    field_value,
    infer_dosage_form,
    quality_gate,
    read_drug_name,
    read_trade_name,
)
from .schema import CollectionManifest, DrugCandidate, DrugRecord, SourceCandidate
from .storage import save_raw_page, save_record, write_outputs


def parse_args() -> Namespace:
    parser = ArgumentParser(description="离线采集智药问点本地中文说明书语料")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("corpus/sources.json"),
        help="候选来源清单",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="原始网页保存目录（必须保持 Git 忽略）",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="TXT、元数据和药品注册表目录（必须保持 Git 忽略）",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=10.0,
        help="串行请求之间的等待秒数",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser.parse_args()


def _unique(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def build_record(
    candidate: DrugCandidate,
    source: SourceCandidate,
    page_bytes: bytes,
    page_text: str,
    fetched_at: str,
) -> DrugRecord:
    extracted = extract_instruction(source.url, page_text)
    quality = quality_gate(candidate, extracted)
    if not quality.accepted:
        raise ValueError("；".join(quality.reasons))

    drug_name = read_drug_name(extracted)
    trade_name = read_trade_name(extracted)
    aliases = _unique([*candidate.aliases, trade_name])
    return DrugRecord(
        drug_id=candidate.drug_id,
        drug_name=drug_name,
        aliases=aliases,
        dosage_form=infer_dosage_form(drug_name),
        specification=field_value(
            extracted.sections.get("规格", ""), ("规格",)
        ),
        manufacturer=field_value(
            extracted.sections["生产企业"], ("企业名称", "生产企业")
        ),
        approval_number=field_value(
            extracted.sections["批准文号"], ("批准文号",)
        ),
        sections=extracted.sections,
        source_site=source.site,
        source_url=source.url,
        fetched_at=fetched_at,
        content_sha256=hashlib.sha256(page_bytes).hexdigest(),
    )


def collect_one(
    candidate: DrugCandidate,
    raw_dir: Path,
    processed_dir: Path,
    user_agent: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    for source in candidate.sources:
        fetched_at = datetime.now(timezone.utc).isoformat()
        try:
            payload, page_text = fetch_page(source, user_agent)
            raw_path = save_raw_page(raw_dir, candidate, source, payload)
            record = build_record(
                candidate, source, payload, page_text, fetched_at
            )
            return save_record(processed_dir, record, raw_path), failures
        except Exception as error:
            failures.append(
                {
                    "site": source.site,
                    "url": source.url,
                    "reason": str(error),
                }
            )
    return None, failures


def main() -> int:
    args = parse_args()
    manifest = CollectionManifest.load(args.manifest)
    if args.delay_seconds < 0:
        raise ValueError("delay-seconds 不能小于 0")

    started_at = datetime.now(timezone.utc).isoformat()
    registry: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    total = len(manifest.drugs)

    for index, candidate in enumerate(manifest.drugs, start=1):
        print(f"[{index}/{total}] 采集 {candidate.expected_drug_name}")
        item, failures = collect_one(
            candidate,
            args.raw_dir,
            args.processed_dir,
            args.user_agent,
        )
        if item:
            registry.append(item)
            print(f"  已通过质量门槛：{item['drug_name']}")
        else:
            rejected.append(
                {
                    "drug_id": candidate.drug_id,
                    "expected_drug_name": candidate.expected_drug_name,
                    "failures": failures,
                }
            )
            print("  所有候选来源均未通过质量门槛", file=sys.stderr)

        if index < total and args.delay_seconds:
            time.sleep(args.delay_seconds)

    registry.sort(key=lambda item: item["drug_id"])
    write_outputs(args.processed_dir, manifest, registry, rejected, started_at)

    print(f"采集完成：通过 {len(registry)}，拒绝 {len(rejected)}")
    if len(registry) < manifest.minimum_required:
        print(
            f"通过数量不足 {manifest.minimum_required}，请为被拒药品补充候选来源后重跑。",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
