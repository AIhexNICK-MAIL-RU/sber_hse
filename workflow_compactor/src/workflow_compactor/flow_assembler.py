"""Turn a compact flow spec string into full Langflow flow dict (nodes + edges grid)."""

from __future__ import annotations

from typing import Any

# Models may wrap answers in reasoning blocks; strip before parsing the spec.
_THINK_CLOSERS = ("</" + "think" + ">", "</" + "redacted" + "_" + "reasoning" + ">")


def assemble_flow_from_spec_text(spec: str) -> dict[str, Any]:
    """Call lfx ``build_flow_from_spec``. Requires ``lfx`` on PYTHONPATH (Langflow install).

    Returns:
        On success: ``{"flow": {...}, "name": ..., "node_count": ..., "edge_count": ..., "node_id_map": ...}``
        On failure: ``{"error": str, "details": str}``
    """
    try:
        from lfx.graph.flow_builder.builder import build_flow_from_spec
    except ImportError as e:
        return {
            "error": "lfx_not_found",
            "details": f"Install Langflow / lfx or set PYTHONPATH to lfx/src: {e}",
        }
    return build_flow_from_spec(spec.strip())


def extract_spec_from_llm_text(raw: str) -> str:
    """Strip optional markdown fences and leading chatter from model output."""
    text = raw.strip()
    for close in _THINK_CLOSERS:
        if close in text:
            text = text.split(close, 1)[-1].strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text
