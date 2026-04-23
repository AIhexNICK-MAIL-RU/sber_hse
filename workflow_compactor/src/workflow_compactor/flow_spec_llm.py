"""Prompts for LLM: emit a compact flow **spec** (many nodes), not a single component JSON."""

from __future__ import annotations

FLOW_SPEC_FORMAT = """
You must output ONLY a flow spec in this exact text format (no markdown fences, no commentary):

name: <short title>
description: <one line>

nodes:
  <id>: <ExactComponentTypeName>
  <id>: <ExactComponentTypeName>
  ...

edges:
  <id>.<output_handle> -> <id>.<input_field>
  ...

Optional config (template field names only, use ids from nodes:):
config:
  <id>.<field_name>: <value>

Rules:
- Output at least 3 nodes whenever the user asks for a workflow, pipeline, or chatbot.
- Use ONLY registry type names from the ALLOWED TYPES list (e.g. ``Prompt Template``, not ``Prompt``).
- Edges must reference real handles (e.g. ChatInput ``message`` -> LanguageModelComponent ``input_value``; ``Prompt Template`` output is often ``prompt`` -> LLM ``system_message``; LLM ``text_output`` -> ChatOutput ``input_value``).
- Prefer a DAG ending in ChatOutput or a sink component when the task is conversational output.
- Do not paste Python component code. Do not output Langflow node JSON. Only the spec format above.
""".strip()


def build_user_message(natural_language: str, allowed_types_block: str) -> str:
    return (
        f"USER REQUEST:\n{natural_language.strip()}\n\n"
        f"ALLOWED COMPONENT TYPES (use these exact strings after colon in nodes:):\n{allowed_types_block}\n\n"
        "Write the flow spec now."
    )
