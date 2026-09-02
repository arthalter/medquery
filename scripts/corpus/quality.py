from __future__ import annotations

from dataclasses import dataclass
import re

from .schema import DrugCandidate, ExtractedInstruction


CRITICAL_SECTIONS = ("适应症", "用法用量", "禁忌", "注意事项")


@dataclass(frozen=True)
class QualityResult:
    accepted: bool
    reasons: tuple[str, ...]


def labeled_value(section: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        matched = re.search(
            rf"(?:^|\n)\s*{re.escape(label)}\s*[：:]\s*(.+?)(?=\n|$)",
            section,
        )
        if matched:
            return matched.group(1).strip()
    return ""


def field_value(section: str, labels: tuple[str, ...]) -> str:
    """读取带标签字段；纯字段章节没有内嵌标签时保留完整内容。"""

    return labeled_value(section, labels) or section.strip()


def normalize_drug_name(value: str) -> str:
    value = re.sub(r"[（(][^）)]*[）)]", "", value)
    return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", value).lower()


def read_drug_name(extracted: ExtractedInstruction) -> str:
    section = extracted.sections.get("药品名称", "")
    value = labeled_value(section, ("通用名称", "药品名称", "名称"))
    if value:
        return value
    title = re.split(r"(?:详细说明书|说明书|-)", extracted.page_title, maxsplit=1)[0]
    return re.sub(r"[（(][^）)]*[）)]", "", title).strip()


def read_trade_name(extracted: ExtractedInstruction) -> str:
    return labeled_value(extracted.sections.get("药品名称", ""), ("商品名称",))


def infer_dosage_form(drug_name: str) -> str:
    forms = (
        "肠溶胶囊",
        "缓释胶囊",
        "软胶囊",
        "肠溶片",
        "缓释片",
        "控释片",
        "分散片",
        "咀嚼片",
        "泡腾片",
        "口崩片",
        "注射液",
        "口服溶液",
        "口服液",
        "混悬液",
        "颗粒",
        "胶囊",
        "滴丸",
        "糖浆",
        "贴剂",
        "乳膏",
        "软膏",
        "凝胶",
        "气雾剂",
        "喷雾剂",
        "散",
        "片",
        "丸",
    )
    for form in forms:
        if drug_name.endswith(form):
            return form
    return "未标明"


def quality_gate(
    candidate: DrugCandidate, extracted: ExtractedInstruction
) -> QualityResult:
    reasons: list[str] = []
    drug_name = read_drug_name(extracted)
    approval_number = field_value(
        extracted.sections.get("批准文号", ""), ("批准文号",)
    )
    manufacturer = field_value(
        extracted.sections.get("生产企业", ""), ("企业名称", "生产企业")
    )
    specification = field_value(
        extracted.sections.get("规格", ""), ("规格",)
    )
    dosage_form = infer_dosage_form(drug_name)

    if not drug_name:
        reasons.append("缺少药名")
    elif normalize_drug_name(drug_name) != normalize_drug_name(
        candidate.expected_drug_name
    ):
        reasons.append(
            f"药名不匹配：期望 {candidate.expected_drug_name}，实际 {drug_name}"
        )
    if not approval_number:
        reasons.append("缺少批准文号")
    if not manufacturer:
        reasons.append("缺少生产企业")
    if not candidate.aliases:
        reasons.append("缺少药品识别别名")
    if not specification:
        reasons.append("缺少规格")
    if dosage_form == "未标明":
        reasons.append("无法从药名识别剂型")

    available = [
        heading
        for heading in CRITICAL_SECTIONS
        if len(extracted.sections.get(heading, "").strip()) >= 2
    ]
    if len(available) < 3:
        reasons.append(
            "适应症、用法用量、禁忌、注意事项四项中不足三项："
            + "、".join(available or ("无",))
        )

    body = "".join(extracted.sections.values())
    if len(re.findall(r"[\u3400-\u9fff]", body)) < 80:
        reasons.append("中文正文过短或页面解析错位")

    return QualityResult(accepted=not reasons, reasons=tuple(reasons))
