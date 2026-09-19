#!/usr/bin/env python3
from __future__ import annotations

import os

from agent.llm import chat, embed


def main() -> None:
    messages = [{"role": "user", "content": "Reply with JSON: {\"status\": \"ok\"}"}]
    chat(os.getenv("MODEL_REASONING", "bedrock/amazon.nova-lite-v1:0"), messages, temperature=0, json=True)
    chat(os.getenv("MODEL_GENERATION", "bedrock/cohere.command-r-plus-v1:0"), messages, temperature=0, json=True)
    chat(os.getenv("MODEL_TRANSLATION", "bedrock/cohere.command-r-plus-v1:0"), messages, temperature=0, json=True)
    embed(["sample invoice text for embedding"])
    print("LLM smoke test passed")


if __name__ == "__main__":
    main()
