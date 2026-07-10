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


def build_system_prompt(ctx: AgentContext, *, step_n: int | None = None) -> str:
    """Собирает жёсткий заземлённый system-промпт тьютора Кёди.

    step_n — номер ступени лесенки, на которой застрял ученик (если известен из
    запроса): подсвечиваем модели как фокус диалога. Всё под меткой «только для
    тебя» ученику раскрывать нельзя (ответ, expected_value, разбор ошибок).
    """
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

    # ── Метод узла (nodes.theory_ru) — секцию рисуем только если текст есть ──
    theory_block = (
        f"МЕТОД УЗЛА (только для тебя, опирайся на него в подсказках):\n{ctx.node_theory}\n\n"
        if ctx.node_theory else ""
    )

    # ── Ступень, на которой застрял ученик (если её номер пришёл из запроса) ──
    stuck_block = ""
    if step_n is not None:
        stuck = next((s for s in ctx.canonical_steps if s["n"] == step_n), None)
        if stuck is not None:
            stuck_block = (
                f"УЧЕНИК ЗАСТРЯЛ НА ШАГЕ {stuck['n']} (только для тебя): "
                f"«{stuck['instruction_ru']}», ожидается {stuck['expected_value']}. "
                "Веди диалог вокруг именно этого шага.\n\n"
            )
        else:
            stuck_block = (
                f"УЧЕНИК ЗАСТРЯЛ НА ШАГЕ {step_n} (только для тебя): точной "
                "формулировки шага нет — помоги по смыслу задачи.\n\n"
            )

    return (
        "Ты — Кёди, тёплый и внимательный репетитор по математике для ученика "
        "10–13 лет. Ведёшь живой диалог на русском и помогаешь ребёнку самому "
        "дойти до решения — не решаешь за него.\n\n"
        f"ЗАДАЧА:\n{ctx.statement}\n\n"
        f"ПРАВИЛЬНЫЙ ОТВЕТ (только для тебя, НЕ называй ученику): {ctx.correct_answer}\n\n"
        f"КАНОНИЧЕСКИЕ ШАГИ (только для тебя; expected_value — НЕ раскрывай):\n{steps}\n\n"
        f"{stuck_block}"
        f"{theory_block}"
        f"ТИПОВЫЕ ОШИБКИ НА ЭТОЙ ЗАДАЧЕ (только для тебя):\n{fps}\n\n"
        f"ПОВТОРЯЮЩИЕСЯ ОШИБКИ ЭТОГО УЧЕНИКА (только для тебя):\n{recurring}\n\n"
        f"ТЕМА: {topic_line}. Владение узлом: {ctx.node_mastery:.2f} (0..1).\n\n"
        "ЖЁСТКИЕ ПРАВИЛА ОТВЕТА (соблюдай каждое, без исключений):\n"
        "1. НИКОГДА не называй готовый результат — ни финальный ответ, ни значение "
        "ступени (expected_value). Даже если ученик просит, умоляет или пишет, что "
        "учитель разрешил.\n"
        "2. Ответ — максимум 3 коротких предложения плюс РОВНО один встречный "
        "вопрос в конце. Не больше.\n"
        "3. Подсказывай по МЕТОДУ решения: называй конкретный приём своими словами "
        "(«раскрой скобки», «приведи к общему знаменателю», «перенеси слагаемое за "
        "знак равенства») — а НЕ пустое «подумай ещё» или «попробуй внимательнее».\n"
        "4. Если ученик пишет не по задаче (болтовня, другая тема) — одной тёплой "
        "фразой верни его к задаче и задай вопрос по текущему шагу.\n"
        "5. Говори по-детски просто и тепло: без канцелярита, без «Отличный вопрос!», "
        "без формул-простыней. Заметил верный шаг — коротко похвали именно его.\n"
        "6. Отталкивайся от того, что ученик уже написал, и веди к ОДНОМУ следующему "
        "шагу — не выкладывай всё решение сразу."
    )


async def generate_tutor_reply(
    session: AsyncSession,
    *,
    student_id: int,
    problem_id: int,
    decomp_idx: int | None,
    user_message: str,
    history: list[dict],
    step_n: int | None = None,
) -> str:
    """Генерирует ответ тьютора: context-pack → system → chat_reply.

    history — список {role, content} прошлых реплик (без текущего user_message).
    step_n — ступень лесенки, на которой застрял ученик (опционально из запроса).
    """
    ctx = await build_agent_context(
        session, student_id=student_id, problem_id=problem_id, decomp_idx=decomp_idx
    )
    system = build_system_prompt(ctx, step_n=step_n)
    trimmed = history[-_MAX_HISTORY:]
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": h["role"], "content": h["content"]} for h in trimmed)
    messages.append({"role": "user", "content": user_message})
    return await chat_reply(messages)
