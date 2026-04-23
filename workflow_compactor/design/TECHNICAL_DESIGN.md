# Langflow JSON Compaction System Design

## 1) Goal and problem statement

The objective is to transform large Langflow workflow JSON exports into a
compact, normalized, and semantically dense representation that is easier for
smaller LLMs to process. The transformed format must preserve operational logic
and dependencies between components while reducing context size and noise.
The system is designed for real-world exports containing thousands of lines and
version-specific service metadata.

## 2) Analysis of Langflow JSON structure

### 2.1 Core entities

Typical workflow exports contain:

- **Nodes/components**: executable blocks with type, parameters, and metadata.
- **Edges/connections**: links from source output ports to target input ports.
- **Graph metadata**: flow name, IDs, timestamps, canvas/UI state.
- **Component payload**: rich nested structures, including defaults and
  provider-specific settings.

### 2.2 Logically critical fields

Critical for behavior reconstruction:

- Node identity (`id`/stable reference)
- Component semantic type (`class`, `type`, or equivalent)
- Effective parameters (actual values, not UI defaults only)
- Input/output ports and edge mappings
- Conditional routing semantics (if/else, branch labels)
- Entry/output nodes and terminal sinks

### 2.3 Mostly service/noise fields

Usually removable or aggressively compressed:

- Canvas coordinates and visual properties
- Frontend-only flags, viewport state
- Repeated default metadata for all nodes
- Full docs/help strings embedded per component
- Redundant snapshots/version traces when not needed for execution

### 2.4 Dependency types

- **Dataflow edges**: value propagation between ports.
- **Control-flow branches**: explicit conditional split/merge.
- **Implicit dependencies**: node references by parameter (e.g., selected tool
  IDs, variable references).

## 3) Target compact format

The target is a two-level format:

1. **Compact IR** (machine-friendly)
2. **Model Summary** (LLM-friendly concise narrative)

### 3.1 Compact IR unit schema

```json
{
  "flow_id": "string",
  "flow_name": "string",
  "version": "cir.v1",
  "nodes": [
    {
      "id": "n1",
      "kind": "llm_prompt",
      "role": "classifier",
      "params": {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "prompt_template": "..."
      },
      "io": {
        "inputs": ["text"],
        "outputs": ["label", "confidence"]
      },
      "flags": {
        "is_conditional": false,
        "is_terminal": false
      }
    }
  ],
  "edges": [
    {
      "from": {"node": "n1", "port": "label"},
      "to": {"node": "n2", "port": "condition_input"},
      "semantics": "data"
    }
  ],
  "control": {
    "entry_nodes": ["n0"],
    "terminal_nodes": ["n9"],
    "branches": [
      {
        "router_node": "n2",
        "cases": [
          {"when": "cat", "target_node": "n3"},
          {"when": "dog", "target_node": "n4"}
        ],
        "default_target": "n5"
      }
    ]
  },
  "integrity": {
    "node_count": 10,
    "edge_count": 12,
    "hash": "sha256:..."
  }
}
```

### 3.2 Why this format works for weak models

- Bounded vocabulary (`kind`, `role`, `semantics`) improves parsing stability.
- Flattened, explicit graph semantics avoids inference from noisy nested payload.
- Parameter subset focuses on behavior-driving values only.
- Branches are represented declaratively, not hidden in arbitrary nested fields.

## 4) Transformation rules

### 4.1 Keep as-is

- Stable node IDs
- Effective component type
- Explicit edge connectivity and port names
- Required behavior-driving params

### 4.2 Normalize

- Canonical node `kind` mapping (provider-specific names -> unified taxonomy)
- Parameter names (`max_tokens`, `temperature`, `threshold`) to canonical keys
- Port naming where aliases exist (`output`, `result`, `text`)

### 4.3 Aggregate

- Large repetitive defaults into shared profile references
- Provider blobs into distilled param object
- Repeated prompt fragments into template references if duplicated

### 4.4 Drop

- UI coordinates/styles
- Timestamps not needed for execution
- Non-operational metadata docs and hints
- Duplicate empty/null fields

### 4.5 Preserve reconstruction capability

Reconstruction does not require byte-level JSON fidelity; it requires semantic
equivalence:

- same executable node set (or mapped equivalents),
- same dependency graph,
- same branch behavior,
- same effective parameters.

Therefore, IR stores an optional `origin_path` for each field and node mapping.

## 5) Implementation architecture

Pipeline stages:

1. **Load & parse**
   - tolerant JSON parser with recovery mode for malformed fragments.
2. **Extract raw graph**
   - identify nodes/edges from known Langflow patterns and fallback heuristics.
3. **Canonicalization**
   - map component types and parameters to taxonomy.
4. **Compaction**
   - remove noise, deduplicate repeated structures, emit Compact IR.
5. **Summary builder**
   - generate LLM-friendly short representation from IR.
6. **Validation**
   - structural checks + semantic checks + metrics.

### 5.1 Intermediate structures

- `RawFlowGraph`: close to source schema.
- `CanonicalFlowGraph`: normalized semantics.
- `CompactIR`: minimal runtime-preserving format.
- `SummaryPacket`: weak-model prompt payload.

### 5.2 Scalability strategy

- Stream parse where possible (for very large files).
- O(N + E) graph transforms; avoid quadratic traversals.
- Hash-based dedup of large param blobs.
- Optional chunked summaries by subgraph/topological layers.

### 5.3 Fault tolerance

- Unknown node types -> `kind: "custom_unknown"` with retained payload digest.
- Missing ports -> inferred placeholders + validation warnings.
- Partial corruption -> best-effort extraction + explicit confidence score.

## 6) Validation and metrics

### 6.1 Validation dimensions

- **Structural integrity**: node/edge consistency, acyclic checks (if expected),
  branch target existence.
- **Semantic retention**: fraction of behavior-critical params preserved.
- **Compactness**: size ratio `compressed_bytes / source_bytes`.
- **LLM suitability**: token count for summary payload under target budget.

### 6.2 Suggested metrics

- `critical_param_recall` >= 0.98
- `edge_recall` == 1.0 for explicit data edges
- `branch_recall` == 1.0 for control branches
- `size_reduction_ratio` <= 0.35 (target, dataset-dependent)
- `summary_tokens` <= model_budget (e.g. 4k / 8k)

### 6.3 Practical test suite

- Golden workflows (small/medium/large)
- Synthetic stress workflows (deep branches, repeated templates)
- Cross-version exports (Langflow version drift)
- Mutated/corrupted exports

## 7) Edge cases and risks

1. **Custom components**
   - risk: unknown schema.
   - handling: classify as custom, retain selective raw payload and warnings.
2. **Implicit dependencies in params**
   - risk: hidden links not represented as edges.
   - handling: parse references and append `semantics: "implicit_ref"` edges.
3. **Cycles**
   - risk: topological summarization fails.
   - handling: SCC condensation graph + cycle annotations.
4. **Over-aggressive pruning**
   - risk: semantic loss.
   - handling: critical field whitelist + regression checks.
5. **Ambiguous branch encoding**
   - risk: wrong if/else reconstruction.
   - handling: branch extractor with confidence + manual review hook.

## 8) Deployment recommendations

- Store both Compact IR and SummaryPacket.
- Keep `origin_mapping` for debuggability and reverse-trace.
- Use Compact IR as default context for weak-model copilot planning/editing.
- Escalate to full JSON only when:
  - low confidence extraction,
  - unresolved custom nodes,
  - validation score below threshold.

Versioning strategy:

- semantic version of compact schema (`cir.v1`, `cir.v2`)
- migration utilities between versions
- compatibility tests against new Langflow exports

This gives a practical, extensible system that is small-model-friendly while
preserving executable workflow logic.

