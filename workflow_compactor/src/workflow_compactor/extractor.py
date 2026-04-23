from __future__ import annotations

from typing import Any


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def detect_graph_root(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Locate flow graph root in different export shapes.
    """
    if "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload


def extract_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract node objects from common Langflow-like export variants.
    """
    candidates = [
        graph.get("nodes"),
        graph.get("vertexes"),
        graph.get("components"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate
    return []


def extract_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract edge/link objects from common Langflow-like export variants.
    """
    candidates = [
        graph.get("edges"),
        graph.get("links"),
        graph.get("connections"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate
    return []


def extract_flow_meta(payload: dict[str, Any], graph: dict[str, Any]) -> tuple[str, str]:
    flow_id = str(graph.get("id") or payload.get("id") or "unknown_flow")
    flow_name = str(
        graph.get("name")
        or payload.get("name")
        or graph.get("display_name")
        or "unnamed_flow"
    )
    return flow_id, flow_name


def extract_node_identity(node: dict[str, Any], fallback_idx: int) -> tuple[str, str]:
    data = _safe_dict(node.get("data"))
    data_node = _safe_dict(data.get("node"))
    metadata = _safe_dict(data_node.get("metadata"))
    node_id = str(node.get("id") or node.get("node_id") or f"n_{fallback_idx}")
    component_type = str(
        data_node.get("type")
        or data.get("type")
        or metadata.get("module", "").split(".")[-1]
        or node.get("class")
        or node.get("type")
        or "unknown"
    )
    return node_id, component_type


def extract_node_params(node: dict[str, Any]) -> dict[str, Any]:
    data = _safe_dict(node.get("data"))
    data_node = _safe_dict(data.get("node"))
    fields = _safe_dict(data.get("fields"))
    template = _safe_dict(data_node.get("template") or data.get("template"))
    params = _safe_dict(data_node)

    if fields:
        return fields
    if template:
        compact_template: dict[str, Any] = {}
        for key, descriptor in template.items():
            if key in {"_type", "code"}:
                continue
            if not isinstance(descriptor, dict):
                compact_template[key] = descriptor
                continue
            if "value" in descriptor:
                compact_template[key] = descriptor.get("value")
            elif "default" in descriptor:
                compact_template[key] = descriptor.get("default")
            elif "selected" in descriptor:
                compact_template[key] = descriptor.get("selected")
        if compact_template:
            return compact_template
    return params


def extract_node_description(node: dict[str, Any]) -> str:
    data = _safe_dict(node.get("data"))
    data_node = _safe_dict(data.get("node"))

    description_candidates = [
        data.get("description"),
        data_node.get("description"),
        data.get("display_name"),
        data_node.get("display_name"),
        data_node.get("metadata", {}).get("module")
        if isinstance(data_node.get("metadata"), dict)
        else None,
        data_node.get("type"),
    ]

    for candidate in description_candidates:
        if isinstance(candidate, str):
            normalized = " ".join(candidate.split()).strip()
            if normalized:
                if len(normalized) > 240:
                    return f"{normalized[:237]}..."
                return normalized
    return "No description available."


def extract_node_ports(node: dict[str, Any]) -> tuple[list[str], list[str]]:
    data = _safe_dict(node.get("data"))
    data_node = _safe_dict(data.get("node"))
    outputs = []
    inputs = []

    for key in ("outputs", "out_ports", "output_ports"):
        output_items = _safe_list(node.get(key) or data.get(key))
        if not output_items:
            output_items = _safe_list(data_node.get(key))
        for item in output_items:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("id") or "output")
            else:
                name = str(item)
            outputs.append(name)
        if outputs:
            break

    for key in ("inputs", "in_ports", "input_ports"):
        input_items = _safe_list(node.get(key) or data.get(key))
        if not input_items:
            input_items = _safe_list(data_node.get(key))
        for item in input_items:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("id") or "input")
            else:
                name = str(item)
            inputs.append(name)
        if inputs:
            break

    return sorted(set(inputs)), sorted(set(outputs))


def extract_edge_ports(edge: dict[str, Any]) -> tuple[str, str, str, str]:
    edge_data = _safe_dict(edge.get("data"))
    source_handle = _safe_dict(edge_data.get("sourceHandle"))
    target_handle = _safe_dict(edge_data.get("targetHandle"))
    src = str(edge.get("source") or edge.get("from") or edge.get("source_id") or "")
    dst = str(edge.get("target") or edge.get("to") or edge.get("target_id") or "")
    src_port = str(
        source_handle.get("name")
        or source_handle.get("fieldName")
        or
        edge.get("sourceHandle")
        or edge.get("source_port")
        or edge.get("from_port")
        or "output"
    )
    dst_port = str(
        target_handle.get("fieldName")
        or target_handle.get("name")
        or
        edge.get("targetHandle")
        or edge.get("target_port")
        or edge.get("to_port")
        or "input"
    )
    return src, src_port, dst, dst_port

