from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PortRef:
    node: str
    port: str


@dataclass
class Edge:
    from_ref: PortRef
    to_ref: PortRef
    semantics: str = "data"

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": asdict(self.from_ref),
            "to": asdict(self.to_ref),
            "semantics": self.semantics,
        }


@dataclass
class Node:
    node_id: str
    kind: str
    role: str
    params: dict[str, Any] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    is_conditional: bool = False
    is_terminal: bool = False
    origin_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "kind": self.kind,
            "role": self.role,
            "params": self.params,
            "io": {"inputs": self.inputs, "outputs": self.outputs},
            "flags": {
                "is_conditional": self.is_conditional,
                "is_terminal": self.is_terminal,
            },
            "origin_type": self.origin_type,
        }


@dataclass
class BranchCase:
    when: str
    target_node: str


@dataclass
class Branch:
    router_node: str
    cases: list[BranchCase]
    default_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "router_node": self.router_node,
            "cases": [asdict(case) for case in self.cases],
            "default_target": self.default_target,
        }


@dataclass
class CompactIR:
    flow_id: str
    flow_name: str
    version: str
    nodes: list[Node]
    edges: list[Edge]
    entry_nodes: list[str]
    terminal_nodes: list[str]
    branches: list[Branch]
    integrity_hash: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "control": {
                "entry_nodes": self.entry_nodes,
                "terminal_nodes": self.terminal_nodes,
                "branches": [branch.to_dict() for branch in self.branches],
            },
            "integrity": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "hash": self.integrity_hash,
            },
            "warnings": self.warnings,
        }

