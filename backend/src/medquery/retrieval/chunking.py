from __future__ import annotations

from dataclasses import dataclass
import re

from medquery.retrieval.models import ChunkPiece


PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
SENTENCE_TERMINATORS = frozenset("。！？!?")
SENTENCE_CLOSERS = frozenset("”’」』）》】\"'")


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    complete: bool


def _period_ends_sentence(text: str, index: int) -> bool:
    previous = text[index - 1] if index else ""
    following = text[index + 1] if index + 1 < len(text) else ""
    if previous.isdigit() and following.isdigit():
        return False
    return not following or following.isspace() or following in SENTENCE_CLOSERS


def split_sentences(text: str) -> list[Sentence]:
    """保留中英文句末标点；末尾无句号的残段不会被当作完整句。"""

    sentences: list[Sentence] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        is_end = char in SENTENCE_TERMINATORS
        if char == ".":
            is_end = _period_ends_sentence(text, index)
        if char == "…" and index + 1 < len(text) and text[index + 1] == "…":
            index += 1
            is_end = True

        if is_end:
            end = index + 1
            while end < len(text) and text[end] in SENTENCE_CLOSERS:
                end += 1
            sentence = text[start:end].strip()
            if sentence:
                sentences.append(Sentence(text=sentence, complete=True))
            start = end
            index = end
            continue
        index += 1

    trailing = text[start:].strip()
    if trailing:
        sentences.append(Sentence(text=trailing, complete=False))
    return sentences


def _split_long_paragraph(paragraph: str, char_limit: int) -> list[str]:
    sentences = split_sentences(paragraph)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for sentence in sentences:
        separator_length = 1 if current else 0
        proposed_length = current_length + separator_length + len(sentence.text)
        if current and proposed_length > char_limit:
            chunks.append("\n".join(current))
            current = []
            current_length = 0

        if not current and len(sentence.text) > char_limit:
            chunks.append(sentence.text)
            continue

        if current:
            current_length += 1
        current.append(sentence.text)
        current_length += len(sentence.text)

    if current:
        chunks.append("\n".join(current))
    return chunks


def _last_complete_sentence(text: str) -> str:
    complete = [item.text for item in split_sentences(text) if item.complete]
    return complete[-1] if complete else ""


def chunk_section(
    section_text: str,
    *,
    char_limit: int,
    overlap_last_sentence: bool,
) -> list[ChunkPiece]:
    """自然段优先切片，上一切片末句作为不计额度的重叠前缀。"""

    if char_limit <= 0:
        raise ValueError("切片字符上限必须大于 0")

    paragraphs = [
        paragraph.strip()
        for paragraph in PARAGRAPH_BREAK.split(section_text.strip())
        if paragraph.strip()
    ]
    bodies: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= char_limit:
            bodies.append(paragraph)
        else:
            bodies.extend(_split_long_paragraph(paragraph, char_limit))

    pieces: list[ChunkPiece] = []
    previous_last_sentence = ""
    for body in bodies:
        overlap = previous_last_sentence if overlap_last_sentence else ""
        pieces.append(ChunkPiece(body=body, overlap=overlap))
        body_last_sentence = _last_complete_sentence(body)
        previous_last_sentence = body_last_sentence or overlap
    return pieces
