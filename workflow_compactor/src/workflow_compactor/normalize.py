from __future__ import annotations

from typing import Any


KIND_MAPPING = {
    "chatinput": "source_text",
    "chatoutput": "sink_text",
    "llm": "llm_inference",
    "languagemodelcomponent": "llm_inference",
    "language_model_component": "llm_inference",
    "prompt": "prompt_template",
    "prompttemplate": "prompt_template",
    "ifelse": "conditional_router",
    "router": "conditional_router",
    "filterdata": "filter",
    "retriever": "retriever",
    "agent": "agent",
    "note": "annotation",
    "notenode": "annotation",
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
    "annotation": "non_executable",
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
    "base_classes",
    "conditional_paths",
    "custom_fields",
    "field_order",
    "metadata",
    "tool_mode",
    "trace_as_input",
    "trace_as_metadata",
    "list_add_label",
    "load_from_db",
    "advanced",
    "dynamic",
    "password",
    "multiline",
    "show",
    "title_case",
    "node",
    "template",
    "code",
    "frozen",
    "legacy",
    "pinned",
    "edited",
    "documentation",
    "lf_version",
}


def _compact_scalar(value: Any) -> Any:
    if isinstance(value, str):
        collapsed = " ".join(value.split())
        if len(collapsed) > 180:
            return f"{collapsed[:177]}..."
        return collapsed
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return None


def _compact_value(value: Any) -> Any:
    scalar = _compact_scalar(value)
    if scalar is not None:
        return scalar
    if isinstance(value, list):
        compact_items = []
        for item in value[:8]:
            compact_item = _compact_scalar(item)
            if compact_item is not None:
                compact_items.append(compact_item)
            elif isinstance(item, dict):
                mini = {}
                for key in ("name", "display_name", "type", "value", "selected"):
                    if key in item:
                        compact_item_value = _compact_scalar(item.get(key))
                        if compact_item_value is not None:
                            mini[key] = compact_item_value
                if mini:
                    compact_items.append(mini)
        if len(value) > 8:
            compact_items.append(f"...(+{len(value) - 8} items)")
        return compact_items
    if isinstance(value, dict):
        mini_dict = {}
        for key in ("value", "selected", "type", "display_name", "fieldName", "name"):
            if key in value:
                compact_item_value = _compact_scalar(value.get(key))
                if compact_item_value is not None:
                    mini_dict[key] = compact_item_value
        return mini_dict or None
    return None


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
            compacted = _compact_value(value)
            if compacted is not None:
                clean[key_norm] = compacted
            continue
        # Keep short keys with compact values to preserve custom behavior.
        if len(key_norm) <= 40:
            compacted = _compact_value(value)
            if compacted is not None:
                clean[key_norm] = compacted
    return clean


def detect_conditional(kind: str, params: dict[str, Any]) -> bool:
    if kind == "conditional_router":
        return True
    return any(k in params for k in ("condition", "if", "else"))

