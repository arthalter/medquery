from __future__ import annotations

from collections.abc import Iterable
from html.parser import HTMLParser
from urllib.parse import urlparse
import html
import re

from .schema import ExtractedInstruction


HEADING_ALIASES = {
    "药品名称": "药品名称",
    "名称": "药品名称",
    "成份": "成份",
    "成分": "成份",
    "性状": "性状",
    "适应症": "适应症",
    "功能主治": "适应症",
    "主治功能": "适应症",
    "用法用量": "用法用量",
    "不良反应": "不良反应",
    "禁忌": "禁忌",
    "注意事项": "注意事项",
    "特殊人群用药": "特殊人群用药",
    "孕妇及哺乳期妇女用药": "孕妇及哺乳期妇女用药",
    "儿童用药": "儿童用药",
    "老年用药": "老年用药",
    "药物相互作用": "药物相互作用",
    "药理作用": "药理作用",
    "药代动力学": "药代动力学",
    "贮藏": "贮藏",
    "规格": "规格",
    "包装规格": "包装规格",
    "有效期": "有效期",
    "执行标准": "执行标准",
    "批准文号": "批准文号",
    "说明书修订日期": "说明书修订日期",
    "生产企业": "生产企业",
}

BODY_SECTION_ORDER = (
    "成份",
    "性状",
    "适应症",
    "用法用量",
    "不良反应",
    "禁忌",
    "注意事项",
    "特殊人群用药",
    "孕妇及哺乳期妇女用药",
    "儿童用药",
    "老年用药",
    "药物相互作用",
    "药理作用",
    "药代动力学",
    "贮藏",
)

BLOCK_TAGS = {
    "article",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}


def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
    for key, value in attrs:
        if key == "class" and value:
            return set(value.split())
    return set()


def _clean_text(parts: Iterable[str]) -> str:
    joined = " ".join(parts)
    joined = html.unescape(joined).replace("\xa0", " ")
    joined = re.sub(r"[ \t\f\v]+", " ", joined)
    joined = re.sub(r"\s*\n\s*", "\n", joined)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def _clean_heading(value: str) -> str:
    value = re.sub(r"^[\s【〖\[（(]+|[\s】〗\]）)]+$", "", value)
    return re.sub(r"[：:]$", "", value).strip()


class Ypk39InstructionParser(HTMLParser):
    """只读取 39 药品通说明书列表，避开导航、广告和推荐内容。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page_title_parts: list[str] = []
        self.sections: dict[str, str] = {}
        self._in_title = False
        self._manual_depth = 0
        self._in_item = False
        self._capture: str | None = None
        self._heading_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        classes = _classes(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "ul" and "drug-explain" in classes:
            self._manual_depth = 1
            return
        if self._manual_depth:
            if tag == "ul":
                self._manual_depth += 1
            if tag == "li" and self._manual_depth == 1:
                self._in_item = True
                self._heading_parts = []
                self._text_parts = []
            if self._in_item and tag == "p":
                if "drug-explain-tit" in classes:
                    self._capture = "heading"
                elif "drug-explain-txt" in classes:
                    self._capture = "text"
            if self._in_item and tag == "br" and self._capture == "text":
                self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if not self._manual_depth:
            return
        if tag == "p":
            self._capture = None
        if tag == "li" and self._in_item and self._manual_depth == 1:
            heading = _clean_heading(_clean_text(self._heading_parts))
            body = _clean_text(self._text_parts)
            canonical = HEADING_ALIASES.get(heading)
            if canonical and body:
                if canonical in self.sections:
                    self.sections[canonical] += "\n" + body
                else:
                    self.sections[canonical] = body
            self._in_item = False
            self._capture = None
        if tag == "ul":
            self._manual_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page_title_parts.append(data)
        if self._capture == "heading":
            self._heading_parts.append(data)
        elif self._capture == "text":
            self._text_parts.append(data)

    def result(self) -> ExtractedInstruction:
        return ExtractedInstruction(
            page_title=_clean_text(self.page_title_parts),
            sections=self.sections,
        )


class VisibleTextParser(HTMLParser):
    """用于家庭医生在线、药源网等备用来源的保守文本提取器。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        if not self._ignored_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.parts.append(data)
        if self._in_title:
            self.title_parts.append(data)


def _extract_generic_sections(text: str) -> dict[str, str]:
    heading_names = sorted(HEADING_ALIASES, key=len, reverse=True)
    heading_pattern = "|".join(re.escape(item) for item in heading_names)
    marker = re.compile(
        rf"^(?:[【〖\[]\s*)?(?P<heading>{heading_pattern})"
        rf"(?:\s*[】〗\]])?\s*[：:]?\s*(?P<tail>.*)$"
    )

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        matched = marker.match(line)
        if matched:
            current = HEADING_ALIASES[matched.group("heading")]
            sections.setdefault(current, [])
            tail = matched.group("tail").strip()
            if tail:
                sections[current].append(tail)
            continue
        if current:
            sections[current].append(line)

    return {
        heading: _clean_text(parts)
        for heading, parts in sections.items()
        if _clean_text(parts)
    }


def extract_instruction(source_url: str, page: str) -> ExtractedInstruction:
    host = urlparse(source_url).hostname or ""
    if host == "ypk.39.net" or host.endswith(".ypk.39.net"):
        parser = Ypk39InstructionParser()
        parser.feed(page)
        result = parser.result()
        if result.sections:
            return result

    parser = VisibleTextParser()
    parser.feed(page)
    visible_text = _clean_text(parser.parts)
    return ExtractedInstruction(
        page_title=_clean_text(parser.title_parts),
        sections=_extract_generic_sections(visible_text),
    )


def build_document_text(sections: dict[str, str]) -> str:
    """只输出正文章节；身份、来源和采集信息全部留在 JSON 元数据中。"""

    blocks = [
        f"【{heading}】\n{sections[heading]}"
        for heading in BODY_SECTION_ORDER
        if sections.get(heading)
    ]
    return "\n\n".join(blocks).strip() + "\n"
