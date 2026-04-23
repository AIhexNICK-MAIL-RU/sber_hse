from __future__ import annotations

from collections import Counter
from typing import Any

from .models import CompactIR


def _infer_fill_source(param_key: str, value: Any) -> str:
    key = param_key.lower()
    if key in {"query", "prompt", "template", "system_prompt", "system_message"}:
        return "prompt"
    if key in {"database", "table", "path"}:
        return "db"
    if key in {"api_key", "token", "password", "secret"}:
        return "user"
    if value in ("", None, "__UNDEFINED__"):
        return "user"
    return "system_default"


def build_summary_packet(ir: CompactIR) -> dict[str, Any]:
    kinds = Counter(node.kind for node in ir.nodes)
    roles = Counter(node.role for node in ir.nodes)
    compatibility = [
        {
            "from": f"{edge.from_ref.node}.{edge.from_ref.port}",
            "to": f"{edge.to_ref.node}.{edge.to_ref.port}",
            "type_compatible": True,
            "conversion_needed": False,
        }
        for edge in ir.edges
    ]
    parameter_fill_plan = []
    component_dictionary = {
        node.node_id: {
            "component_type": node.origin_type or node.kind,
            "description": node.description,
            "kind": node.kind,
            "role": node.role,
        }
        for node in ir.nodes
    }
    executable_component_dictionary = {
        node.node_id: component_dictionary[node.node_id]
        for node in ir.nodes
        if node.kind != "annotation"
    }
    for node in ir.nodes:
        for key, value in node.params.items():
            parameter_fill_plan.append(
                {
                    "node": node.node_id,
                    "field": key,
                    "source": _infer_fill_source(key, value),
                    "required": value in ("", None, "__UNDEFINED__"),
                }
            )

    return {
        "flow": {
            "id": ir.flow_id,
            "name": ir.flow_name,
            "version": ir.version,
        },
        "shape": {
            "nodes": len(ir.nodes),
            "edges": len(ir.edges),
            "entry_nodes": ir.entry_nodes,
            "terminal_nodes": ir.terminal_nodes,
            "branch_count": len(ir.branches),
        },
        "composition": {
            "kinds": dict(kinds),
            "roles": dict(roles),
        },
        "execution_outline": [
            {
                "node_id": node.node_id,
                "kind": node.kind,
                "role": node.role,
                "description": node.description,
                "critical_params": node.params,
            }
            for node in ir.nodes
        ],
        "component_dictionary": component_dictionary,
        "executable_component_dictionary": executable_component_dictionary,
        "planning_json": {
            "candidate_components": [
                {
                    "component_id": node.origin_type or node.kind,
                    "node_id": node.node_id,
                    "description": component_dictionary.get(node.node_id, {}).get(
                        "description", ""
                    ),
                    "kind": node.kind,
                    "role": node.role,
                    "outputs": node.outputs,
                    "inputs": node.inputs,
                }
                for node in ir.nodes
                if node.kind != "annotation"
            ],
            "connections": [
                {
                    "from": f"{edge.from_ref.node}.{edge.from_ref.port}",
                    "to": f"{edge.to_ref.node}.{edge.to_ref.port}",
                }
                for edge in ir.edges
            ],
            "parameter_fill_plan": parameter_fill_plan,
        },
        "compatibility_graph": compatibility,
        "integrity_hash": ir.integrity_hash,
        "warnings": ir.warnings,
    }

