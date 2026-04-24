from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .component_retrieval import search_component_cards
from .copilot import generate_agent_response, generate_copilot_response
from .flow_assembler import assemble_flow_from_spec_text
from .planning_engine import make_plan_packet
from .summary import build_summary_packet
from .transformer import compact_workflow

app = FastAPI(title="Workflow Copilot API", version="0.1.0")


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str = "workflow-copilot"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None


class AgentRequest(BaseModel):
    query: str = Field(min_length=1)
    workflow_json: dict[str, Any] | None = None


class AssembleFromSpecRequest(BaseModel):
    spec: str = Field(min_length=1, description="Compact flow spec for lfx build_flow_from_spec")


class PlanRequest(BaseModel):
    query: str = Field(min_length=1)


class ApprovedAssembleRequest(BaseModel):
    query: str = Field(min_length=1)
    spec: str = Field(min_length=1)
    approved: bool = Field(default=False)


class ComponentSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=80)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "workflow-copilot-api",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


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


@app.post("/v1/components/search")
def components_search(request: ComponentSearchRequest) -> dict[str, Any]:
    """BM25 over component_index cards (names + descriptions, no full templates)."""
    hits = search_component_cards(request.query, top_k=request.top_k)
    return {"query": request.query, "count": len(hits), "components": hits}


@app.post("/v1/workflow/assemble-from-spec")
def workflow_assemble_from_spec(request: AssembleFromSpecRequest) -> dict[str, Any]:
    """Turn a compact spec into full Langflow flow JSON (requires lfx on PYTHONPATH)."""
    return assemble_flow_from_spec_text(request.spec)


@app.post("/v1/copilot/plan")
def copilot_plan(request: PlanRequest) -> dict[str, Any]:
    """Create Task Card + feasibility gate + planning outline from user query."""
    packet = make_plan_packet(request.query)
    return {"query": request.query, **packet}


@app.post("/v1/workflow/assemble-approved")
def workflow_assemble_approved(request: ApprovedAssembleRequest) -> dict[str, Any]:
    """Compile to execution JSON only after explicit user approval."""
    if not request.approved:
        return {
            "ok": False,
            "error": "approval_required",
            "details": "Set approved=true to compile execution JSON.",
            "plan": make_plan_packet(request.query),
        }
    result = assemble_flow_from_spec_text(request.spec)
    return {"ok": "error" not in result, "plan": make_plan_packet(request.query), "result": result}


@app.post("/v1/agent/query")
def agent_query(request: AgentRequest) -> dict[str, Any]:
    workflow_context = None
    if request.workflow_json:
        ir = compact_workflow(request.workflow_json)
        workflow_context = build_summary_packet(ir)
    answer = generate_agent_response(request.query, workflow_context)
    return {
        "query": request.query,
        "answer": answer,
        "has_workflow_context": workflow_context is not None,
        "workflow_context": workflow_context,
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "workflow_compactor.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )

