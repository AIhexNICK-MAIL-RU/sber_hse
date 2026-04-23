from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .copilot import generate_copilot_response

app = FastAPI(title="Workflow Copilot API", version="0.1.0")


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str = "workflow-copilot"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": "workflow-copilot",
                "object": "model",
                "created": now,
                "owned_by": "workflow_compactor",
            }
        ],
    }


def _extract_user_text(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role != "user":
            continue
        if isinstance(msg.content, str):
            return msg.content
        parts = []
        for item in msg.content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        if parts:
            return "\n".join(parts)
    return ""


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
    user_query = _extract_user_text(request.messages)
    answer = generate_copilot_response(user_query)
    now = int(time.time())
    return {
        "id": f"chatcmpl-{now}",
        "object": "chat.completion",
        "created": now,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(user_query) // 4),
            "completion_tokens": max(1, len(answer) // 4),
            "total_tokens": max(2, (len(user_query) + len(answer)) // 4),
        },
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "workflow_compactor.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )

