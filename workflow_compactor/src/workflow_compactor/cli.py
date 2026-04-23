from __future__ import annotations

import argparse
import json
from pathlib import Path

from .summary import build_summary_packet
from .transformer import compact_workflow
from .validate import validate_ir


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


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
    args = parser.parse_args()

    source_path = Path(args.input)
    out_ir = Path(args.out_ir)
    out_summary = Path(args.out_summary)
    out_report = Path(args.report)

    source = _read_json(source_path)
    ir = compact_workflow(source)
    summary = build_summary_packet(ir)
    report = validate_ir(ir, source)

    _write_json(out_ir, ir.to_dict())
    _write_json(out_summary, summary)
    _write_json(out_report, report)

    print("Compaction complete.")
    print(f"IR: {out_ir}")
    print(f"Summary: {out_summary}")
    print(f"Report: {out_report}")


if __name__ == "__main__":
    main()

