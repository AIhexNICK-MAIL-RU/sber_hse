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
    node_id = str(node.get("id") or node.get("node_id") or f"n_{fallback_idx}")
    component_type = str(
        node.get("type")
        or node.get("class")
        or _safe_dict(node.get("data")).get("type")
        or "unknown"
    )
    return node_id, component_type


def extract_node_params(node: dict[str, Any]) -> dict[str, Any]:
    data = _safe_dict(node.get("data"))
    fields = _safe_dict(data.get("fields"))
    template = _safe_dict(data.get("template"))
    params = _safe_dict(data.get("node"))

    if fields:
        return fields
    if template:
        return template
    return params


def extract_node_ports(node: dict[str, Any]) -> tuple[list[str], list[str]]:
    data = _safe_dict(node.get("data"))
    outputs = []
    inputs = []

    for key in ("outputs", "out_ports", "output_ports"):
        output_items = _safe_list(node.get(key) or data.get(key))
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
    src = str(edge.get("source") or edge.get("from") or edge.get("source_id") or "")
    dst = str(edge.get("target") or edge.get("to") or edge.get("target_id") or "")
    src_port = str(
        edge.get("sourceHandle")
        or edge.get("source_port")
        or edge.get("from_port")
        or "output"
    )
    dst_port = str(
        edge.get("targetHandle")
        or edge.get("target_port")
        or edge.get("to_port")
        or "input"
    )
    return src, src_port, dst, dst_port

