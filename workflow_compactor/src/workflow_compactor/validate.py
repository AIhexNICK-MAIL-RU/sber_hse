from __future__ import annotations

from typing import Any

from .models import CompactIR


def validate_ir(ir: CompactIR, source: dict[str, Any]) -> dict[str, Any]:
    """
    Basic structural and retention report.
    """
    issues: list[str] = []

    node_ids = {node.node_id for node in ir.nodes}
    for edge in ir.edges:
        if edge.from_ref.node not in node_ids:
            issues.append(f"edge source missing in nodes: {edge.from_ref.node}")
        if edge.to_ref.node not in node_ids:
            issues.append(f"edge target missing in nodes: {edge.to_ref.node}")

    for branch in ir.branches:
        if branch.router_node not in node_ids:
            issues.append(f"branch router missing in nodes: {branch.router_node}")
        for case in branch.cases:
            if case.target_node not in node_ids:
                issues.append(
                    f"branch case target missing in nodes: {case.target_node}"
                )

    source_size = len(str(source))
    compact_size = len(str(ir.to_dict()))
    size_reduction_ratio = compact_size / source_size if source_size else 1.0

    return {
        "ok": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "warnings": ir.warnings,
        "metrics": {
            "source_chars": source_size,
            "compact_chars": compact_size,
            "size_reduction_ratio": round(size_reduction_ratio, 4),
            "node_count": len(ir.nodes),
            "edge_count": len(ir.edges),
            "branch_count": len(ir.branches),
        },
    }

