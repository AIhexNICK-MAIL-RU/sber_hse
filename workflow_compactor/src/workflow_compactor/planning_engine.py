from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "explain": (
        "объясни",
        "как работает",
        "что делает",
        "почему",
        "зачем",
        "что такое",
    ),
    "edit": (
        "измени",
        "добавь",
        "замени",
        "исправь",
        "перенаправь",
        "поменяй",
        "update",
        "replace",
    ),
    "build": (
        "построй",
        "собери",
        "сгенерируй",
        "workflow",
        "flow",
        "pipeline",
        "цепочку",
        "сеть из компонент",
    ),
    "consult": (
        "посоветуй",
        "рекоменда",
        "best practice",
        "подход",
        "архитектур",
    ),
}


@dataclass
class TaskCard:
    goal: str = ""
    inputs: list[str] = field(default_factory=list)
    expected_result: str = ""
    constraints: list[str] = field(default_factory=list)
    external_context: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_intent(query: str) -> str:
    q = query.lower().strip()
    if not q:
        return "consult"
    for intent in ("explain", "edit", "build", "consult"):
        if any(token in q for token in _INTENT_KEYWORDS[intent]):
            return intent
    return "build"


def _extract_inputs(text: str) -> list[str]:
    candidates = []
    for token in ("json", "csv", "xlsx", "pdf", "email", "api", "таблиц", "чат", "prompt"):
        if token in text:
            candidates.append(token)
    return sorted(set(candidates))


def _extract_constraints(text: str) -> list[str]:
    constraints = []
    for marker in ("без", "только", "не ", "limit", "timeout", "sla", "дедлайн"):
        if marker in text:
            constraints.append(f"contains:{marker}")
    return constraints


def build_task_card(query: str) -> TaskCard:
    q = query.strip()
    q_low = q.lower()
    card = TaskCard(
        goal=q,
        inputs=_extract_inputs(q_low),
        expected_result="Готовый workflow для импорта в Langflow canvas",
        constraints=_extract_constraints(q_low),
    )
    if any(token in q_low for token in ("s3", "postgres", "notion", "jira", "crm")):
        card.external_context.append("Есть внешний источник данных/система")
    if any(token in q_low for token in ("api key", "token", "секрет", "ключ")):
        card.external_context.append("Нужен секрет/credential")
    return card


def feasibility_gate(task_card: TaskCard, intent: str) -> dict[str, Any]:
    missing: list[str] = []
    if not task_card.goal:
        missing.append("goal")
    if intent in {"build", "edit"} and not task_card.inputs:
        missing.append("inputs")
    if intent == "build" and not task_card.expected_result:
        missing.append("expected_result")
    task_card.missing_info = missing
    return {"ready": not missing, "missing": missing}


def clarification_questions(missing: list[str]) -> list[str]:
    mapping = {
        "goal": "Какую бизнес-цель должен решать итоговый workflow?",
        "inputs": "Какие входные данные используются (формат, источник, пример)?",
        "expected_result": "Какой формат результата ожидается на выходе?",
    }
    return [mapping[item] for item in missing if item in mapping]


def _draft_connections(intent: str) -> list[dict[str, str]]:
    if intent == "edit":
        return [{"action": "patch", "scope": "planning_spec", "mode": "targeted"}]
    return [
        {"from": "ChatInput.message", "to": "LanguageModelComponent.input_value"},
        {"from": "PromptTemplate.prompt", "to": "LanguageModelComponent.system_message"},
        {"from": "LanguageModelComponent.text_output", "to": "ChatOutput.input_value"},
    ]


def build_planning_outline(query: str, intent: str) -> dict[str, Any]:
    q_low = query.lower()
    candidates = ["ChatInput", "PromptTemplate", "LanguageModelComponent", "ChatOutput"]
    if any(token in q_low for token in ("if", "ветв", "router", "услов")):
        candidates.append("IfElseComponent")
    if any(token in q_low for token in ("csv", "таблиц", "dataset")):
        candidates.append("File")
    return {
        "task_sections": ["goal", "inputs", "expected_result", "constraints", "external_context"],
        "candidate_components": candidates,
        "connections": _draft_connections(intent),
        "parameter_fill_plan": [
            {"field": "model", "source": "default"},
            {"field": "temperature", "source": "default"},
            {"field": "api_key", "source": "user"},
        ],
    }


def make_plan_packet(query: str) -> dict[str, Any]:
    intent = classify_intent(query)
    card = build_task_card(query)
    gate = feasibility_gate(card, intent)
    questions = clarification_questions(gate["missing"])
    return {
        "intent": intent,
        "task_card": card.to_dict(),
        "feasibility": gate,
        "clarification_questions": questions,
        "planning_outline": build_planning_outline(query, intent),
        "requires_approval": intent in {"build", "edit"} and gate["ready"],
        "hard_stop_policy": {
            "max_repair_iterations": 3,
            "max_total_seconds": 45,
            "fallback": "partial_result_with_blockers",
        },
    }


def apply_parameter_edit_patch(
    planning_outline: dict[str, Any], edit_text: str
) -> dict[str, Any]:
    """Tiny patch helper for parameter-level edits.

    Supports phrases like 'temperature 0.2' or 'model gpt-4o-mini'.
    """
    patched = dict(planning_outline)
    plan = list(patched.get("parameter_fill_plan", []))
    lowered = edit_text.lower()
    for field in ("temperature", "model"):
        if field not in lowered:
            continue
        m = re.search(rf"{field}\s*[:=]?\s*([A-Za-z0-9._-]+)", lowered)
        if not m:
            continue
        value = m.group(1)
        plan.append({"field": field, "source": "user", "value": value})
    patched["parameter_fill_plan"] = plan
    return patched
