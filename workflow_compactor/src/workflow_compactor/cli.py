from __future__ import annotations

import argparse
import json
from pathlib import Path

from .summary import build_summary_packet
from .transformer import compact_workflow
from .validate import validate_ir
from .visualize import (
    build_dashboard_html,
    build_svg_diagram,
    build_visualization_markdown,
)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact Langflow workflow JSON.")
    parser.add_argument("--input", required=True, help="Path to source JSON.")
    parser.add_argument("--out-ir", required=True, help="Path to compact IR output.")
    parser.add_argument(
        "--out-summary",
        required=True,
        help="Path to weak-model summary output.",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to validation report output.",
    )
    parser.add_argument(
        "--out-visualization",
        required=False,
        help="Optional path to Markdown visualization output (Mermaid).",
    )
    parser.add_argument(
        "--out-dashboard-html",
        required=False,
        help="Optional path to HTML dashboard output for presentation.",
    )
    parser.add_argument(
        "--out-diagram-svg",
        required=False,
        help="Optional path to standalone SVG diagram for slides.",
    )
    args = parser.parse_args()

    source_path = Path(args.input)
    out_ir = Path(args.out_ir)
    out_summary = Path(args.out_summary)
    out_report = Path(args.report)
    out_visualization = Path(args.out_visualization) if args.out_visualization else None
    out_dashboard_html = Path(args.out_dashboard_html) if args.out_dashboard_html else None
    out_diagram_svg = Path(args.out_diagram_svg) if args.out_diagram_svg else None

    source = _read_json(source_path)
    ir = compact_workflow(source)
    summary = build_summary_packet(ir)
    report = validate_ir(ir, source)
    svg_diagram = build_svg_diagram(ir)

    _write_json(out_ir, ir.to_dict())
    _write_json(out_summary, summary)
    _write_json(out_report, report)
    if out_visualization is not None:
        _write_text(out_visualization, build_visualization_markdown(ir))
    if out_diagram_svg is not None:
        _write_text(out_diagram_svg, svg_diagram)
    if out_dashboard_html is not None:
        _write_text(out_dashboard_html, build_dashboard_html(ir, summary, report, svg_diagram))

    print("Compaction complete.")
    print(f"IR: {out_ir}")
    print(f"Summary: {out_summary}")
    print(f"Report: {out_report}")
    if out_visualization is not None:
        print(f"Visualization: {out_visualization}")
    if out_diagram_svg is not None:
        print(f"Diagram SVG: {out_diagram_svg}")
    if out_dashboard_html is not None:
        print(f"Dashboard HTML: {out_dashboard_html}")


if __name__ == "__main__":
    main()

