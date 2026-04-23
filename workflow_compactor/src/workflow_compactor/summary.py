from __future__ import annotations

from collections import Counter
from typing import Any

from .models import CompactIR


def build_summary_packet(ir: CompactIR) -> dict[str, Any]:
    kinds = Counter(node.kind for node in ir.nodes)
    roles = Counter(node.role for node in ir.nodes)

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
                "critical_params": node.params,
            }
            for node in ir.nodes
        ],
        "integrity_hash": ir.integrity_hash,
        "warnings": ir.warnings,
    }

