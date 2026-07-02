"""Чат-тьютор: сократический диалог поверх grounding-пакета.

Строит system-промпт из AgentContext (условие, шаги, правильный ответ, ошибки,
mastery), запрещает раскрывать финальный ответ, вызывает chat_reply.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.agent_context import AgentContext, build_agent_context
from core.llm_openai import chat_reply

# Максимум реплик истории, передаваемых модели (защита контекста/цены)
_MAX_HISTORY = 20


def build_system_prompt(ctx: AgentContext) -> str:
    """Собирает сократический system-промпт из grounding-пакета."""
    steps = "\n".join(
        f"  Шаг {s['n']}: {s['instruction_ru']} → {s['expected_value']}"
        for s in ctx.canonical_steps
    ) or "  (шаги недоступны)"
    fps = "\n".join(
        f"  - {f['micro_skill']}: неверный ответ «{f['wrong_answer']}» — {f['mistake_ru']}"
        for f in ctx.fingerprints
    ) or "  (нет типовых ошибок)"
    recurring = "\n".join(
        f"  - {r['micro_skill']}: {r['error_count']} раз(а); {r['last_cause_text'] or ''}"
        for r in ctx.recurring_errors
    ) or "  (нет повторяющихся ошибок)"
    topic_line = f"{ctx.topic['name_ru']} ({ctx.topic['strand']})" if ctx.topic else "—"

    return (
        "Ты — доброжелательный математический тьютор Кёди. Ведёшь диалог с учеником "
        "на русском, помогаешь разобрать ошибку в конкретной задаче.\n\n"
        f"ЗАДАЧА:\n{ctx.statement}\n\n"
        f"ПРАВИЛЬНЫЙ ОТВЕТ (для тебя, НЕ называй ученику): {ctx.correct_answer}\n\n"
        f"КАНОНИЧЕСКИЕ ШАГИ:\n{steps}\n\n"
        f"ТИПОВЫЕ ОШИБКИ НА ЭТОЙ ЗАДАЧЕ:\n{fps}\n\n"
        f"ПОВТОРЯЮЩИЕСЯ ОШИБКИ ЭТОГО УЧЕНИКА:\n{recurring}\n\n"
        f"ТЕМА: {topic_line}. Владение узлом: {ctx.node_mastery:.2f} (0..1).\n\n"
        "ПРАВИЛА ДИАЛОГА:\n"
        "1. Задавай наводящие вопросы, веди к решению по шагам — НИКОГДА не называй "
        "финальный ответ напрямую.\n"
        "2. Отталкивайся от того, что ученик уже написал; хвали верные шаги.\n"
        "3. Пиши коротко (2-4 предложения), по-человечески, без формул-простыней.\n"
        "4. Если ученик застрял — дай подсказку на ОДИН следующий шаг, не на всё решение."
    )


async def generate_tutor_reply(
    session: AsyncSession,
    *,
    student_id: int,
    problem_id: int,
    decomp_idx: int | None,
    user_message: str,
    history: list[dict],
) -> str:
    """Генерирует ответ тьютора: context-pack → system → chat_reply.

    history — список {role, content} прошлых реплик (без текущего user_message).
    """
    ctx = await build_agent_context(
        session, student_id=student_id, problem_id=problem_id, decomp_idx=decomp_idx
    )
    system = build_system_prompt(ctx)
    trimmed = history[-_MAX_HISTORY:]
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": h["role"], "content": h["content"]} for h in trimmed)
    messages.append({"role": "user", "content": user_message})
    return await chat_reply(messages)
