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
- `examples/` — только исходные workflow в обычном Langflow JSON (`Basic Prompting.json` из starter projects, плюс `input_sample.json` для минимального теста). Сжатый IR, summary и отчёты в репозиторий не кладём; их можно получить локально командой CLI ниже.

## Quick start

```bash
cd workflow_compactor
mkdir -p .generated
python3 -m workflow_compactor.cli \
  --input ./examples/Basic\ Prompting.json \
  --out-ir ./.generated/output_ir.json \
  --out-summary ./.generated/output_summary.json \
  --report ./.generated/validation_report.json \
  --out-visualization ./.generated/workflow_visualization.md \
  --out-diagram-svg ./.generated/workflow_diagram.svg \
  --out-dashboard-html ./.generated/workflow_dashboard.html
```

Каталог `.generated/` при желании добавьте в `.gitignore` — это производные файлы компактификации, не «нормальный» экспорт Langflow.

`--out-visualization` creates a Markdown file with a Mermaid graph and
step-by-step execution outline.

`--out-diagram-svg` exports a standalone SVG image for slides.

`--out-dashboard-html` exports a presentation-ready dashboard:
- top KPI cards (nodes/edges/branches/size/compression),
- rendered graph,
- component and role distribution,
- execution outline,
- parameter fill plan.

Summary JSON now also includes `component_dictionary`:
- key: node id
- value: component type + plain-language description.

For cleaner component selection it also includes
`executable_component_dictionary` (same structure, but excludes
`annotation`/`note` nodes).

This dictionary is used by the agent layer to reason about components without
loading heavy Python code from node templates.

## Run with OpenWebUI

From `workflow_compactor/` (all-in-docker):

```bash
docker compose -f docker-compose.openwebui.yml up --build
```

For cloud platforms with different autodetect rules, minimal API-only compose
files are provided with all common names:
`docker-compose.yml`, `docker-compose.yaml`, and `compose.yaml`.
Static `container_name` is intentionally omitted to avoid conflicts across
redeploys in shared Docker hosts.

Then open:

- OpenWebUI: `http://localhost:3000`
- Copilot API health: `http://localhost:8000/health`
- Agent endpoint: `POST http://localhost:8000/v1/agent/query`

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

## Agent query API

You can send a plain query:

```bash
curl -X POST "http://localhost:8000/v1/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"сделай черновой workflow для анализа жалоб за 2 недели"}'
```

Or pass query + workflow JSON context:

```bash
curl -X POST "http://localhost:8000/v1/agent/query" \
  -H "Content-Type: application/json" \
  -d @agent_request_with_workflow.json
```

## Goals of the compact format

1. Preserve execution logic of the workflow.
2. Remove UI/service noise and repetitive payload.
3. Keep only semantically relevant node config and graph connectivity.
4. Produce a stable and bounded-size representation for smaller models.

