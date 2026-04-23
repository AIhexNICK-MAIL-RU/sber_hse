from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from .extractor import (
    detect_graph_root,
    extract_edge_ports,
    extract_edges,
    extract_flow_meta,
    extract_node_identity,
    extract_node_params,
    extract_node_ports,
    extract_nodes,
)
from .models import Branch, BranchCase, CompactIR, Edge, Node, PortRef
from .normalize import detect_conditional, infer_role, normalize_kind, normalize_params


def _hash_graph(nodes: list[Node], edges: list[Edge]) -> str:
    payload = {
        "nodes": [node.to_dict() for node in nodes],
        "edges": [edge.to_dict() for edge in edges],
    }
    dump = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(dump.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _infer_entry_terminal_nodes(nodes: list[Node], edges: list[Edge]) -> tuple[list[str], list[str]]:
    incoming = defaultdict(int)
    outgoing = defaultdict(int)
    for edge in edges:
        outgoing[edge.from_ref.node] += 1
        incoming[edge.to_ref.node] += 1

    node_ids = {node.node_id for node in nodes}
    entry = sorted(node_id for node_id in node_ids if incoming[node_id] == 0)
    terminal = sorted(node_id for node_id in node_ids if outgoing[node_id] == 0)

    return entry, terminal


def _extract_branches(nodes: list[Node], edges: list[Edge]) -> list[Branch]:
    router_ids = {node.node_id for node in nodes if node.is_conditional}
    if not router_ids:
        return []

    grouped_targets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in edges:
        if edge.from_ref.node in router_ids:
            grouped_targets[edge.from_ref.node].append((edge.from_ref.port, edge.to_ref.node))

    branches: list[Branch] = []
    for router, targets in grouped_targets.items():
        cases = []
        default_target = None
        for port, target in targets:
            lower_port = port.lower()
            if "default" in lower_port:
                default_target = target
            else:
                cases.append(BranchCase(when=port, target_node=target))
        branches.append(Branch(router_node=router, cases=cases, default_target=default_target))
    return branches


def compact_workflow(payload: dict[str, Any]) -> CompactIR:
    graph = detect_graph_root(payload)
    flow_id, flow_name = extract_flow_meta(payload, graph)

    raw_nodes = extract_nodes(graph)
    raw_edges = extract_edges(graph)

    nodes: list[Node] = []
    warnings: list[str] = []
    existing_ids = set()

    for idx, raw_node in enumerate(raw_nodes):
        node_id, raw_type = extract_node_identity(raw_node, fallback_idx=idx)
        if node_id in existing_ids:
            warnings.append(f"duplicate node id detected: {node_id}; keeping first occurrence")
            continue
        existing_ids.add(node_id)

        kind = normalize_kind(raw_type)
        role = infer_role(kind)
        params = normalize_params(extract_node_params(raw_node))
        inputs, outputs = extract_node_ports(raw_node)

        node = Node(
            node_id=node_id,
            kind=kind,
            role=role,
            params=params,
            inputs=inputs,
            outputs=outputs,
            is_conditional=detect_conditional(kind, params),
            origin_type=raw_type,
        )
        nodes.append(node)

    edges: list[Edge] = []
    for raw_edge in raw_edges:
        src, src_port, dst, dst_port = extract_edge_ports(raw_edge)
        if not src or not dst:
            warnings.append("edge skipped: missing source or target")
            continue
        if src not in existing_ids or dst not in existing_ids:
            warnings.append(f"edge references unknown node: {src} -> {dst}")
            continue
        edges.append(
            Edge(
                from_ref=PortRef(node=src, port=src_port),
                to_ref=PortRef(node=dst, port=dst_port),
            )
        )

    entry_nodes, terminal_nodes = _infer_entry_terminal_nodes(nodes, edges)
    branches = _extract_branches(nodes, edges)
    terminal_set = set(terminal_nodes)
    for node in nodes:
        node.is_terminal = node.node_id in terminal_set

    integrity_hash = _hash_graph(nodes, edges)

    return CompactIR(
        flow_id=flow_id,
        flow_name=flow_name,
        version="cir.v1",
        nodes=nodes,
        edges=edges,
        entry_nodes=entry_nodes,
        terminal_nodes=terminal_nodes,
        branches=branches,
        integrity_hash=integrity_hash,
        warnings=warnings,
    )

