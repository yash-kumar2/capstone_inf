from __future__ import annotations

import re
from typing import Iterable

from agent.llm import embed as llm_embed


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    if text is None:
        return []
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []

    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n+", cleaned) if segment.strip()]
    if not paragraphs:
        paragraphs = [cleaned]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if not current:
            current = paragraph
            continue
        if len(current) + 1 + len(paragraph) <= size:
            current = f"{current}\n\n{paragraph}"
            continue
        chunks.append(current.strip())
        if len(paragraph) > size:
            words = paragraph.split()
            buffer = ""
            for word in words:
                if len(buffer) + 1 + len(word) <= size:
                    buffer = f"{buffer} {word}".strip()
                else:
                    if buffer:
                        chunks.append(buffer.strip())
                    buffer = word
            if buffer:
                current = buffer.strip()
        else:
            current = paragraph

    if current:
        chunks.append(current.strip())

    if not chunks:
        return [cleaned[:size]]

    final: list[str] = []
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            final.append(chunk)
            continue
        prev = final[-1]
        if len(chunk) > size:
            chunk = chunk[:size]
        if len(prev) + len(chunk) <= size + overlap:
            final[-1] = f"{prev} {chunk}".strip()
        else:
            final.append(chunk)

    return [item.strip() for item in final if item.strip()]


def embed(texts: Iterable[str]) -> list[list[float]]:
    values = list(texts)
    if not values:
        return []
    return llm_embed(values)
