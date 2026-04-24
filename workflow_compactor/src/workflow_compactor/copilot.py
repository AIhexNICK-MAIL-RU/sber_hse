from __future__ import annotations

from typing import Any

from .planning_engine import make_plan_packet


def _build_component_draft(query: str) -> list[str]:
    base = [
        "1) Source: выбрать источник данных (таблица/диалоги/API).",
        "2) Filter: ограничить период/условия отбора.",
        "3) Transform: LLM-классификация или извлечение признаков.",
        "4) Router: условные ветвления if/else по меткам.",
        "5) Aggregate: сводка и агрегация результатов.",
        "6) Output: выгрузка CSV/XLSX или отправка в канал.",
    ]
    q = query.lower()
    if "кот" in q or "собак" in q:
        base.insert(4, "4.1) Branch: if text=cat -> поток A, else if text=dog -> поток B.")
    if "почт" in q or "email" in q:
        base[-1] = "6) Output: выгрузка + отправка email."
    return base


def generate_copilot_response(query: str) -> str:
    packet = make_plan_packet(query)
    intent = packet["intent"]
    draft = "\n".join(f"- {step}" for step in _build_component_draft(query))
    task_card = packet["task_card"]
    feasibility = packet["feasibility"]
    questions = packet["clarification_questions"]
    stop_policy = packet["hard_stop_policy"]

    card_lines = (
        f"- Goal: {task_card.get('goal', '')}\n"
        f"- Inputs: {', '.join(task_card.get('inputs', [])) or 'не определены'}\n"
        f"- Expected Result: {task_card.get('expected_result', 'не определен')}\n"
        f"- Constraints: {', '.join(task_card.get('constraints', [])) or 'нет'}\n"
        f"- External Context: {', '.join(task_card.get('external_context', [])) or 'нет'}"
    )

    if not feasibility.get("ready", False) and intent in {"build", "edit"}:
        questions_text = "\n".join(f"- {q}" for q in questions) or "- Уточните входные параметры."
        return (
            f"### Режим: {intent}\n"
            "Недостаточно данных для сборки/редактирования workflow.\n\n"
            "**Task Card (черновик):**\n"
            f"{card_lines}\n\n"
            "**Что критически отсутствует:**\n"
            f"- {', '.join(feasibility.get('missing', []))}\n\n"
            "**Пакет уточнений (одним блоком):**\n"
            f"{questions_text}\n\n"
            "После ответов покажу planning plan и попрошу approve перед сборкой execution JSON."
        )

    if intent == "explain":
        return (
            "### Режим: explain\n"
            "Понял, что сейчас важнее объяснение, а не автосборка графа.\n\n"
            "Что делает copilot:\n"
            "- интерпретирует задачу на естественном языке;\n"
            "- подбирает совместимые компоненты Langflow;\n"
            "- строит валидный граф с параметрами и ветвлениями;\n"
            "- показывает diff изменений и риски.\n\n"
            "Если хочешь, следующим сообщением переведу это в черновой workflow под твою задачу."
        )

    if intent == "edit":
        return (
            "### Режим: редактирование\n"
            "Понял запрос как изменение существующего workflow.\n\n"
            "План безопасного редактирования:\n"
            "- найти затронутые узлы и их зависимости;\n"
            "- применить замену/правку параметров;\n"
            "- провалидировать входы/выходы и ветвления;\n"
            "- вернуть diff: что изменено, что требует проверки.\n\n"
            "Уточнение: пришли текущий flow JSON или опиши, какой узел нужно изменить первым."
        )

    example_spec = (
        "name: NL Chat Draft\n"
        "description: Минимальный чат из компонентов каталога\n\n"
        "nodes:\n"
        "  A: ChatInput\n"
        "  B: Prompt Template\n"
        "  C: LanguageModelComponent\n"
        "  D: ChatOutput\n\n"
        "edges:\n"
        "  A.message -> C.input_value\n"
        "  B.prompt -> C.system_message\n"
        "  C.text_output -> D.input_value\n"
    )
    return (
        f"### Режим: {intent}\n"
        "Собираю **план графа** (несколько узлов + рёбра), а не один JSON-компонент.\n\n"
        f"**Что понял:** {query}\n\n"
        "**Task Card:**\n"
        f"{card_lines}\n\n"
        "**Feasibility Gate:**\n"
        f"- ready: {feasibility.get('ready', False)}\n"
        f"- missing: {', '.join(feasibility.get('missing', [])) or 'нет'}\n\n"
        "**Черновой pipeline (логика):**\n"
        f"{draft}\n\n"
        "**Approve policy:**\n"
        "- Сначала показываю planning outline и параметры.\n"
        "- Сборка execution JSON только после подтверждения пользователя.\n\n"
        "**Hard stop policy:**\n"
        f"- max_repair_iterations: {stop_policy.get('max_repair_iterations')}\n"
        f"- max_total_seconds: {stop_policy.get('max_total_seconds')}\n"
        f"- fallback: {stop_policy.get('fallback')}\n\n"
        "**Формат для сборщика Langflow (lfx ``build_flow_from_spec``):**\n"
        "Модель должна выдать **только** такой текстовый spec; затем бэкенд подставляет "
        "шаблоны из ``component_index.json`` и получает полный flow с ``data.nodes`` и ``data.edges``.\n\n"
        "Пример spec:\n"
        f"{example_spec}\n"
        "**Следующие шаги:**\n"
        "- retrieval: сузить список допустимых ``ComponentType`` под запрос;\n"
        "- LLM генерирует spec только из этого списка;\n"
        "- ``assemble_flow_from_spec_text`` → готовый JSON workflow для импорта в канву.\n"
    )


def generate_agent_response(query: str, workflow_context: dict[str, Any] | None = None) -> str:
    base = generate_copilot_response(query)
    if not workflow_context:
        return (
            "### Агент Copilot\n"
            "Принял запрос. Работаю без контекста workflow JSON.\n\n"
            f"{base}"
        )

    flow = workflow_context.get("flow", {})
    shape = workflow_context.get("shape", {})
    planning = workflow_context.get("planning_json", {})
    component_dictionary = workflow_context.get("component_dictionary", {})
    candidate_components = planning.get("candidate_components", [])
    component_names = ", ".join(
        str(item.get("component_id", item.get("kind", "unknown")))
        for item in candidate_components[:6]
    ) or "нет данных"
    component_descriptions = []
    for node_id, metadata in list(component_dictionary.items())[:4]:
        description = str(metadata.get("description", "")).strip()
        if not description:
            continue
        component_descriptions.append(f"- `{node_id}`: {description}")
    component_descriptions_text = (
        "\n".join(component_descriptions) if component_descriptions else "- описания недоступны"
    )
    return (
        "### Агент Copilot\n"
        "Принял запрос и использую контекст сжатого workflow.\n\n"
        f"- Flow: `{flow.get('name', 'unnamed')}`\n"
        f"- Узлы/связи: `{shape.get('nodes', 0)}` / `{shape.get('edges', 0)}`\n"
        f"- Ключевые компоненты: {component_names}\n\n"
        f"**Словарь компонентов (id -> описание):**\n{component_descriptions_text}\n\n"
        f"{base}"
    )

