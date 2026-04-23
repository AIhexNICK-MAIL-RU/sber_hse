from __future__ import annotations

from typing import Any


KIND_MAPPING = {
    "chatinput": "source_text",
    "chatoutput": "sink_text",
    "llm": "llm_inference",
    "prompt": "prompt_template",
    "ifelse": "conditional_router",
    "router": "conditional_router",
    "filterdata": "filter",
    "retriever": "retriever",
    "agent": "agent",
}

ROLE_BY_KIND = {
    "source_text": "source",
    "sink_text": "sink",
    "llm_inference": "transform",
    "prompt_template": "transform",
    "conditional_router": "router",
    "filter": "filter",
    "retriever": "retrieval",
    "agent": "orchestrator",
}

CRITICAL_PARAM_KEYS = {
    "model",
    "temperature",
    "max_tokens",
    "prompt",
    "system_prompt",
    "template",
    "threshold",
    "condition",
    "top_k",
    "database",
    "table",
    "path",
    "query",
}

UI_NOISE_KEYS = {
    "x",
    "y",
    "position",
    "width",
    "height",
    "selected",
    "color",
    "icon",
    "documentation",
    "description",
    "placeholder",
}


def normalize_kind(raw_component_type: str) -> str:
    key = raw_component_type.lower().replace(" ", "").replace("_", "")
    return KIND_MAPPING.get(key, "custom_unknown")


def infer_role(kind: str) -> str:
    return ROLE_BY_KIND.get(kind, "custom")


def normalize_params(raw_params: dict[str, Any]) -> dict[str, Any]:
    """
    Keep behavior-driving params and remove obvious UI/service noise.
    """
    clean: dict[str, Any] = {}
    for key, value in raw_params.items():
        key_norm = str(key).strip()
        if key_norm.lower() in UI_NOISE_KEYS:
            continue
        if key_norm in CRITICAL_PARAM_KEYS:
            clean[key_norm] = value
            continue
        # Keep short scalar keys to preserve possible custom behavior.
        if isinstance(value, (str, int, float, bool)) and len(key_norm) <= 40:
            clean[key_norm] = value
    return clean


def detect_conditional(kind: str, params: dict[str, Any]) -> bool:
    if kind == "conditional_router":
        return True
    return any(k in params for k in ("condition", "if", "else"))

