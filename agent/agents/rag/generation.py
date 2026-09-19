from __future__ import annotations

from typing import Any

from agent.llm import chat as llm_chat


def generate_answer(question: str, context: str | list[str], model_key: str | None = None) -> str:
    context_text = "\n\n".join(context) if isinstance(context, list) else (context or "")
    if not context_text:
        return "I could not find evidence in the provided context."

    if llm_chat is None:  # pragma: no cover
        return context_text[:400]

    prompt = (
        "Answer only using the supplied context. If the context is insufficient, say the records do not contain the answer. "
        f"Question: {question}\nContext:\n{context_text}"
    )
    try:
        return llm_chat(model_key or "bedrock/cohere.command-r-plus-v1:0", [{"role": "user", "content": prompt}], temperature=0, cache=True)
    except Exception:
        return context_text[:400]
