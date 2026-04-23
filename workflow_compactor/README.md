# Workflow Compactor for Langflow

This folder contains a practical starter implementation for compacting large
Langflow workflow JSON files into a normalized representation designed for
smaller LLMs.

## What is included

- `design/TECHNICAL_DESIGN.md` — engineering design document with architecture,
  transformation rules, validation strategy, and risk handling.
- `src/workflow_compactor/` — Python implementation skeleton:
  - parsing and extraction from Langflow JSON
  - normalization into compact IR
  - summary generation for weak models
  - integrity checks between source and compacted graph
- `src/workflow_compactor/api.py` — OpenAI-compatible API layer for UI
  integration (OpenWebUI).
- `docker-compose.openwebui.yml` — local UI stack: OpenWebUI + Copilot API.
- `examples/` — placeholders for input/output samples.

## Quick start

```bash
cd workflow_compactor
python3 -m workflow_compactor.cli \
  --input /path/to/langflow_export.json \
  --out-ir ./examples/output_ir.json \
  --out-summary ./examples/output_summary.json \
  --report ./examples/validation_report.json
```

## Run with OpenWebUI

From `workflow_compactor/` (all-in-docker):

```bash
docker compose -f docker-compose.openwebui.yml up --build
```

Then open:

- OpenWebUI: `http://localhost:3000`
- Copilot API health: `http://localhost:8000/health`

OpenWebUI is preconfigured to use the local OpenAI-compatible endpoint:
`http://workflow-copilot-api:8000/v1`.

### If Docker build has slow PyPI/network access

Run API locally and OpenWebUI in Docker:

```bash
# terminal 1 (from repository root)
PYTHONPATH="workflow_compactor/src" python3 -m workflow_compactor.api

# terminal 2
cd workflow_compactor
docker compose -f docker-compose.openwebui.local-api.yml up
```

In this mode OpenWebUI uses:
`http://host.docker.internal:8000/v1`

## Goals of the compact format

1. Preserve execution logic of the workflow.
2. Remove UI/service noise and repetitive payload.
3. Keep only semantically relevant node config and graph connectivity.
4. Produce a stable and bounded-size representation for smaller models.

