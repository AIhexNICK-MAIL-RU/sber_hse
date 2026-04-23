from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Any

from .models import CompactIR


def _sanitize_label(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ").strip()


def _kind_label(kind: str) -> str:
    return kind.replace("_", " ")


def _role_color(role: str) -> str:
    palette = {
        "source": "#D1FAE5",
        "sink": "#DBEAFE",
        "transform": "#FEF3C7",
        "router": "#FDE68A",
        "filter": "#E9D5FF",
        "retrieval": "#FCE7F3",
        "orchestrator": "#FED7AA",
        "non_executable": "#E5E7EB",
    }
    return palette.get(role, "#E5E7EB")


def _compute_levels(ir: CompactIR) -> dict[str, int]:
    incoming: dict[str, int] = {node.node_id: 0 for node in ir.nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in ir.edges:
        outgoing[edge.from_ref.node].append(edge.to_ref.node)
        incoming[edge.to_ref.node] = incoming.get(edge.to_ref.node, 0) + 1
    queue = [node_id for node_id, count in incoming.items() if count == 0]
    if not queue:
        queue = [node.node_id for node in ir.nodes]
    levels = {node_id: 0 for node_id in queue}
    while queue:
        current = queue.pop(0)
        current_level = levels.get(current, 0)
        for nxt in outgoing.get(current, []):
            if current_level + 1 > levels.get(nxt, 0):
                levels[nxt] = current_level + 1
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)
    for node in ir.nodes:
        levels.setdefault(node.node_id, 0)
    return levels


def build_svg_diagram(ir: CompactIR) -> str:
    levels = _compute_levels(ir)
    columns: dict[int, list[str]] = defaultdict(list)
    for node in ir.nodes:
        columns[levels[node.node_id]].append(node.node_id)
    for nodes in columns.values():
        nodes.sort()

    node_width = 280
    node_height = 96
    x_step = 360
    y_step = 150
    margin_x = 60
    margin_y = 60

    positions: dict[str, tuple[int, int]] = {}
    max_rows = 1
    for col_idx in sorted(columns):
        col_nodes = columns[col_idx]
        max_rows = max(max_rows, len(col_nodes))
        for row_idx, node_id in enumerate(col_nodes):
            x = margin_x + col_idx * x_step
            y = margin_y + row_idx * y_step
            positions[node_id] = (x, y)

    width = margin_x * 2 + max(1, len(columns)) * x_step
    height = margin_y * 2 + max_rows * y_step
    node_index = {node.node_id: node for node in ir.nodes}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
        '<polygon points="0 0, 10 3.5, 0 7" fill="#475569" />',
        "</marker>",
        "</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#F8FAFC"/>',
    ]

    for edge in ir.edges:
        src_pos = positions.get(edge.from_ref.node)
        dst_pos = positions.get(edge.to_ref.node)
        if not src_pos or not dst_pos:
            continue
        x1 = src_pos[0] + node_width
        y1 = src_pos[1] + node_height // 2
        x2 = dst_pos[0]
        y2 = dst_pos[1] + node_height // 2
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        lines.append(
            f'<path d="M {x1} {y1} C {mx} {y1}, {mx} {y2}, {x2} {y2}" stroke="#475569" stroke-width="2" fill="none" marker-end="url(#arrow)" />'
        )
        lines.append(
            f'<text x="{mx}" y="{my - 6}" font-size="12" text-anchor="middle" fill="#334155">{escape(edge.from_ref.port)}</text>'
        )

    for node_id, (x, y) in positions.items():
        node = node_index[node_id]
        fill_color = _role_color(node.role)
        lines.append(
            f'<rect x="{x}" y="{y}" rx="12" ry="12" width="{node_width}" height="{node_height}" fill="{fill_color}" stroke="#334155" stroke-width="1.5" />'
        )
        lines.append(
            f'<text x="{x + 14}" y="{y + 30}" font-size="14" font-weight="700" fill="#0F172A">{escape(node_id)}</text>'
        )
        lines.append(
            f'<text x="{x + 14}" y="{y + 52}" font-size="13" fill="#1E293B">{escape(_kind_label(node.kind))}</text>'
        )
        lines.append(
            f'<text x="{x + 14}" y="{y + 72}" font-size="12" fill="#334155">role: {escape(node.role)}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def build_dashboard_html(
    ir: CompactIR,
    summary: dict[str, Any],
    report: dict[str, Any],
    svg_diagram: str,
) -> str:
    metrics = report.get("metrics", {})
    ratio = metrics.get("size_reduction_ratio", 1.0)
    reduction_percent = round((1 - float(ratio)) * 100, 2) if ratio <= 1 else -round((float(ratio) - 1) * 100, 2)
    kinds = summary.get("composition", {}).get("kinds", {})
    roles = summary.get("composition", {}).get("roles", {})
    execution_outline = summary.get("execution_outline", [])
    param_plan = summary.get("planning_json", {}).get("parameter_fill_plan", [])

    kind_rows = "\n".join(
        f"<tr><td>{escape(str(kind))}</td><td>{count}</td></tr>" for kind, count in kinds.items()
    )
    role_rows = "\n".join(
        f"<tr><td>{escape(str(role))}</td><td>{count}</td></tr>" for role, count in roles.items()
    )
    execution_rows = "\n".join(
        "<tr>"
        f"<td>{idx}</td>"
        f"<td>{escape(str(item.get('node_id', '')))}</td>"
        f"<td>{escape(str(item.get('kind', '')))}</td>"
        f"<td>{escape(str(item.get('role', '')))}</td>"
        "</tr>"
        for idx, item in enumerate(execution_outline, start=1)
    )
    param_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('node', '')))}</td>"
        f"<td>{escape(str(item.get('field', '')))}</td>"
        f"<td>{escape(str(item.get('source', '')))}</td>"
        f"<td>{'yes' if item.get('required') else 'no'}</td>"
        "</tr>"
        for item in param_plan[:40]
    )
    embedded_svg = svg_diagram.replace('<?xml version="1.0" encoding="UTF-8"?>', "").strip()

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Workflow Dashboard - {escape(ir.flow_name)}</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #cbd5e1;
      --accent: #2563eb;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    }}
    h1, h2 {{
      margin: 0 0 12px 0;
    }}
    .subtitle {{
      color: var(--muted);
      margin-bottom: 20px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .value {{
      font-size: 22px;
      font-weight: 700;
    }}
    .section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid #e2e8f0;
      padding: 8px 6px;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .svg-wrap {{
      overflow: auto;
      border: 1px dashed var(--border);
      border-radius: 8px;
      padding: 8px;
      background: #fff;
    }}
    .note {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <h1>Workflow Dashboard: {escape(ir.flow_name)}</h1>
  <div class="subtitle">Готово для презентации: метрики, структура, план заполнения параметров и граф выполнения.</div>

  <div class="cards">
    <div class="card"><div class="label">Nodes</div><div class="value">{metrics.get("node_count", 0)}</div></div>
    <div class="card"><div class="label">Edges</div><div class="value">{metrics.get("edge_count", 0)}</div></div>
    <div class="card"><div class="label">Branches</div><div class="value">{metrics.get("branch_count", 0)}</div></div>
    <div class="card"><div class="label">Source chars</div><div class="value">{metrics.get("source_chars", 0)}</div></div>
    <div class="card"><div class="label">Compact chars</div><div class="value">{metrics.get("compact_chars", 0)}</div></div>
    <div class="card"><div class="label">Compression</div><div class="value">{reduction_percent}%</div></div>
  </div>

  <div class="section">
    <h2>Graph (SVG)</h2>
    <div class="svg-wrap">
{embedded_svg}
    </div>
    <div class="note">SVG можно сохранить как файл и вставить в презентацию как векторную картинку.</div>
  </div>

  <div class="two-col">
    <div class="section">
      <h2>Component Kinds</h2>
      <table>
        <thead><tr><th>Kind</th><th>Count</th></tr></thead>
        <tbody>{kind_rows}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Roles</h2>
      <table>
        <thead><tr><th>Role</th><th>Count</th></tr></thead>
        <tbody>{role_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Execution Outline</h2>
    <table>
      <thead><tr><th>#</th><th>Node</th><th>Kind</th><th>Role</th></tr></thead>
      <tbody>{execution_rows}</tbody>
    </table>
  </div>

  <div class="section">
    <h2>Parameter Fill Plan (Top 40)</h2>
    <table>
      <thead><tr><th>Node</th><th>Field</th><th>Source</th><th>Required</th></tr></thead>
      <tbody>{param_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""


def build_mermaid_flow(ir: CompactIR) -> str:
    lines = ["flowchart TD"]
    for node in ir.nodes:
        node_label = _sanitize_label(f"{node.node_id}\\n{_kind_label(node.kind)}")
        lines.append(f'  {node.node_id}["{node_label}"]')
    for edge in ir.edges:
        port = _sanitize_label(edge.from_ref.port)
        lines.append(f"  {edge.from_ref.node} -- {port} --> {edge.to_ref.node}")
    return "\n".join(lines)


def build_visualization_markdown(ir: CompactIR) -> str:
    mermaid = build_mermaid_flow(ir)
    lines = [
        f"# Workflow Visualization: {ir.flow_name}",
        "",
        "## Graph",
        "```mermaid",
        mermaid,
        "```",
        "",
        "## Execution Steps",
    ]
    for idx, node in enumerate(ir.nodes, start=1):
        lines.append(f"{idx}. `{node.node_id}` - `{node.kind}` ({node.role})")
    lines.append("")
    lines.append("## Key Connections")
    for edge in ir.edges:
        lines.append(
            f"- `{edge.from_ref.node}.{edge.from_ref.port}` -> `{edge.to_ref.node}.{edge.to_ref.port}`"
        )
    if ir.branches:
        lines.append("")
        lines.append("## Conditional Branches")
        for branch in ir.branches:
            lines.append(f"- Router: `{branch.router_node}`")
            for case in branch.cases:
                lines.append(f"  - when `{case.when}` -> `{case.target_node}`")
            if branch.default_target:
                lines.append(f"  - default -> `{branch.default_target}`")
    return "\n".join(lines) + "\n"

