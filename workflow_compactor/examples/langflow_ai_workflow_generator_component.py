# ruff: noqa: I001 — paste-friendly single block for Langflow Custom Component
"""
AI Copilot Workflow Generator — custom component for Langflow.

Problem: asking an LLM for "Langflow JSON" usually returns **one node template**,
not a full graph. This component instead:
  1) retrieves candidate **registry type names** (BM25 over component_index);
  2) asks the LLM for a **compact flow spec** (nodes + edges list);
  3) calls ``lfx.graph.flow_builder.builder.build_flow_from_spec`` → full flow dict
     with ``data.nodes`` and ``data.edges`` (grid-ready).

Setup:
  - ``pip install -e /path/to/workflow_compactor`` in the same environment as Langflow, **or**
  - add ``workflow_compactor/src`` to PYTHONPATH.

Ollama: set base URL (default http://127.0.0.1:11434) and model (e.g. qwen3:8b).

Paste the **class body below** (from ``import json``) into Langflow → Components → Custom Component.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput, StrInput
from lfx.schema.data import Data
from lfx.template.field.base import Output

try:
    from workflow_compactor.component_retrieval import search_component_cards
    from workflow_compactor.flow_assembler import assemble_flow_from_spec_text, extract_spec_from_llm_text
    from workflow_compactor.flow_spec_llm import FLOW_SPEC_FORMAT, build_user_message
except ImportError as e:
    search_component_cards = None  # type: ignore[assignment]
    assemble_flow_from_spec_text = None  # type: ignore[assignment]
    extract_spec_from_llm_text = None  # type: ignore[assignment]
    FLOW_SPEC_FORMAT = ""  # type: ignore[assignment]
    build_user_message = None  # type: ignore[assignment]
    _IMPORT_ERROR = str(e)
else:
    _IMPORT_ERROR = ""


def _ollama_chat(*, base_url: str, model: str, system: str, user: str, timeout_s: float = 120.0) -> str:
    url = base_url.rstrip("/") + "/api/chat"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    msg = payload.get("message") or {}
    return str(msg.get("content") or "")


class AIWorkflowGeneratorComponent(Component):
    display_name = "AI Copilot Workflow Generator"
    description = "Converts natural language queries to full Langflow workflows (nodes + edges)."
    icon = "Workflow"
    name = "AIWorkflowGenerator"

    inputs = [
        MessageTextInput(
            name="natural_language_request",
            display_name="Natural Language Request",
            info="Describe the workflow you want (e.g. chat with system prompt and LLM).",
            required=True,
        ),
        StrInput(
            name="ollama_base_url",
            display_name="Ollama base URL",
            value="http://127.0.0.1:11434",
        ),
        StrInput(
            name="ollama_model",
            display_name="Ollama model",
            value="qwen3:8b",
        ),
    ]

    outputs = [
        Output(
            display_name="Workflow JSON",
            name="workflow_json",
            method="build_workflow",
        ),
    ]

    def build_workflow(self) -> Data:
        if search_component_cards is None or assemble_flow_from_spec_text is None:
            return Data(
                data={
                    "error": "workflow_compactor_not_importable",
                    "details": _IMPORT_ERROR or "unknown",
                    "hint": "pip install -e workflow_compactor or add workflow_compactor/src to PYTHONPATH",
                }
            )

        query = str(self.natural_language_request or "").strip()
        if not query:
            return Data(data={"error": "empty_request"})

        cards = search_component_cards(query, top_k=28)
        allowed_lines = [f"- {c['name']} ({c['category']}): {c['display_name']}" for c in cards]
        allowed_block = "\n".join(allowed_lines)
        system = FLOW_SPEC_FORMAT
        user = build_user_message(query, allowed_block)

        try:
            raw = _ollama_chat(
                base_url=str(self.ollama_base_url or "http://127.0.0.1:11434"),
                model=str(self.ollama_model or "qwen3:8b"),
                system=system,
                user=user,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return Data(data={"error": "ollama_request_failed", "details": str(e)})

        spec = extract_spec_from_llm_text(raw)
        if not re.search(r"(?m)^nodes:\s*$", spec):
            return Data(
                data={
                    "error": "llm_did_not_return_flow_spec",
                    "raw_preview": spec[:2000],
                    "hint": "Ask the model again; output must start with name:/nodes:/edges: sections.",
                }
            )

        result: dict[str, Any] = assemble_flow_from_spec_text(spec)
        if result.get("error"):
            return Data(
                data={
                    "error": result.get("error"),
                    "details": result.get("details"),
                    "spec": spec,
                }
            )

        flow = result.get("flow")
        return Data(
            data={
                "workflow": flow,
                "workflow_json": json.dumps(flow, ensure_ascii=False, indent=2),
                "node_count": result.get("node_count"),
                "edge_count": result.get("edge_count"),
                "spec_used": spec,
            }
        )
