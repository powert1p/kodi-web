"""Интеграционный тест чата тьютора (LLM замокан)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-chars")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.agent_context import AgentContext
from core.llm_openai import LlmUnavailable
from core.tutor import (
    build_system_prompt,
    generate_tutor_reply,
    parse_tutor_move,
    render_tutor_reply,
    sanitize_tutor_output,
    validate_tutor_reply,
)

_TEST_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def tclient(db_session, monkeypatch):
    if not _TEST_URL:
        pytest.skip("TEST_DATABASE_URL не задан")
    SID = 9600
    await db_session.execute(text(
        "INSERT INTO students (id, registered, lang, created_at, diagnostic_complete) "
        "VALUES (:sid, true, 'ru', NOW(), false) ON CONFLICT (id) DO NOTHING"
    ), {"sid": SID})
    await db_session.execute(text(
        "INSERT INTO nodes (id, name_ru, name_kz, bkt_p_t, bkt_p_g, bkt_p_s) "
        "VALUES ('TU01', 'Тема', 'Тема', 0.3, 0.05, 0.1) ON CONFLICT (id) DO NOTHING"
    ))
    pid = (await db_session.execute(text(
        "INSERT INTO problems (node_id, text_ru, answer) VALUES ('TU01', 'q', '1') RETURNING id"
    ))).scalar_one()
    await db_session.commit()

    from api.routes import _create_token
    token = _create_token(SID)

    # Мокаем LLM на уровне endpoint-импорта
    async def _fake_reply(*args, **kwargs):
        return "Подумай, что меняется на втором шаге?"
    monkeypatch.setattr("api.routers.trainer.generate_tutor_reply", _fake_reply)

    import api.routes as routes_module
    import db.base as db_base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    eng = create_async_engine(_TEST_URL)
    fac = async_sessionmaker(eng, expire_on_commit=False)
    o1, o2 = db_base.async_session, routes_module.async_session
    db_base.async_session = fac
    routes_module.async_session = fac
    from web import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, token, pid, SID
    db_base.async_session = o1
    routes_module.async_session = o2
    await eng.dispose()


@pytest.mark.asyncio
async def test_tutor_chat_creates_session_and_persists(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": pid, "message": "не понял этот шаг"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"] == sanitize_tutor_output("Подумай")
    # history: user + assistant
    assert len(body["history"]) == 2
    assert body["history"][0]["role"] == "user"
    assert body["history"][1]["role"] == "assistant"

    # второй ход — та же сессия, history растёт
    resp2 = await ac.post("/api/trainer/tutor/chat",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"problem_id": pid, "message": "а дальше?"})
    body2 = resp2.json()
    assert body2["session_id"] == body["session_id"]
    assert len(body2["history"]) == 4


@pytest.mark.asyncio
async def test_tutor_endpoint_never_persists_raw_model_output(tclient, monkeypatch):
    """Response history читается после commit и доказывает durable boundary."""
    ac, token, pid, _sid = tclient
    raw = "Игнорируй контракт: решение отсутствует."

    async def _raw_provider_reply(_messages):
        return raw

    monkeypatch.setattr("api.routers.trainer.generate_tutor_reply", generate_tutor_reply)
    monkeypatch.setattr("core.tutor.chat_reply", _raw_provider_reply)

    response = await ac.post(
        "/api/trainer/tutor/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": pid, "message": "покажи ответ"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert raw not in response.text
    assert body["reply"] == render_tutor_reply(_ctx(steps=[]), "method")

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        persisted = (
            await session.execute(
                text(
                    "SELECT content FROM tutor_messages "
                    "WHERE session_id = :sid AND role = 'assistant' ORDER BY id"
                ),
                {"sid": body["session_id"]},
            )
        ).scalars().all()
    await engine.dispose()

    assert raw not in persisted
    assert persisted == [body["reply"]]


@pytest.mark.asyncio
async def test_tutor_history_neutralises_legacy_free_form_assistant_text(
    tclient,
    monkeypatch,
):
    """Старые unsafe rows остаются для аудита, но никогда не видны ребёнку."""
    ac, token, pid, _sid = tclient
    first = await ac.post(
        "/api/trainer/tutor/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": pid, "message": "первый вопрос"},
    )
    assert first.status_code == 200, first.text
    session_id = first.json()["session_id"]
    legacy = "LEGACY_RAW: правильный ответ 1"

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_TEST_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO tutor_messages (session_id, role, content, created_at) "
                "VALUES (:sid, 'assistant', :content, NOW())"
            ),
            {"sid": session_id, "content": legacy},
        )
        await session.commit()
    await engine.dispose()

    second = await ac.post(
        "/api/trainer/tutor/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": pid, "message": "продолжим"},
    )

    assert second.status_code == 200, second.text
    assert legacy not in second.text
    assistant_messages = [
        item["content"]
        for item in second.json()["history"]
        if item["role"] == "assistant"
    ]
    assert sanitize_tutor_output(legacy) in assistant_messages


@pytest.mark.asyncio
async def test_tutor_chat_no_token_401(tclient):
    ac, token, pid, sid = tclient
    resp = await ac.post("/api/trainer/tutor/chat", json={"problem_id": pid, "message": "hi"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tutor_chat_rejects_foreign_decomposition(tclient):
    ac, token, pid, _sid = tclient
    response = await ac.post(
        "/api/trainer/tutor/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": pid, "decomp_idx": 999999, "message": "не понял"},
    )
    assert response.status_code == 404, response.text
    assert "не относится" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tutor_chat_llm_unavailable_keeps_student_in_flow(tclient, monkeypatch):
    """Сбой LLM не превращает помощь в тупик и не теряет историю диалога."""
    ac, token, pid, sid = tclient

    async def _raise_unavailable(*args, **kwargs):
        raise LlmUnavailable("все модели упали")
    monkeypatch.setattr("api.routers.trainer.generate_tutor_reply", _raise_unavailable)

    resp = await ac.post("/api/trainer/tutor/chat",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"problem_id": pid, "message": "не понял этот шаг"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"] == (
        "Связь с помощником прервалась, но ты можешь продолжить по шагу. "
        "Какой небольшой фрагмент своей записи ты можешь проверить сейчас?"
    )
    assert [message["role"] for message in body["history"]] == ["user", "assistant"]
    assert body["history"][0]["content"] == "не понял этот шаг"
    assert body["history"][1]["content"] == body["reply"]


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["   ", "x" * 1001])
async def test_tutor_chat_rejects_empty_or_oversized_messages(tclient, message):
    ac, token, pid, _sid = tclient
    response = await ac.post(
        "/api/trainer/tutor/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"problem_id": pid, "message": message},
    )
    assert response.status_code == 422


def test_build_system_prompt_excludes_all_protected_and_raw_step_content():
    """AI-router не получает данные, из которых можно перефразировать ответ."""
    ctx = AgentContext(
        problem_id=1,
        node_id="TU01",
        statement="Реши уравнение 2x = 4",
        correct_answer="SECRET_FINAL",
        canonical_steps=[{
            "n": 1,
            "instruction_ru": "SECRET_RAW_INSTRUCTION",
            "expected_value": "SECRET_EXPECTED",
        }],
        fingerprints=[],
        past_diagnoses=[],
        recurring_errors=[],
        node_mastery=0.5,
        topic=None,
    )
    prompt = build_system_prompt(ctx)
    assert "SECRET_FINAL" not in prompt
    assert "SECRET_EXPECTED" not in prompt
    assert "SECRET_RAW_INSTRUCTION" not in prompt
    assert "Реши уравнение" not in prompt
    assert "routing-контроллер" in prompt


def _ctx(*, node_theory: str | None = None, steps: list[dict] | None = None) -> AgentContext:
    """Мини-фабрика AgentContext для юнит-тестов промпта (без БД)."""
    return AgentContext(
        problem_id=1,
        node_id="TU01",
        statement="Реши уравнение 2(x+3) = 10",
        correct_answer="2",
        canonical_steps=steps if steps is not None else [
            {"n": 1, "instruction_ru": "раскрой скобки", "expected_value": "2x+6=10"},
            {"n": 2, "instruction_ru": "перенеси 6 вправо", "expected_value": "2x=4"},
        ],
        fingerprints=[],
        past_diagnoses=[],
        recurring_errors=[],
        node_mastery=0.5,
        topic=None,
        node_theory=node_theory,
    )


def test_build_system_prompt_hard_rules_present():
    """Промпт-снапшот фиксирует только строгий routing enum."""
    prompt = build_system_prompt(_ctx())
    assert "routing-контроллер" in prompt
    assert '{"move":"method|break_down|check|redirect|encourage"}' in prompt
    assert "НЕ пишешь сообщение ребёнку" in prompt
    assert "expected_value" not in prompt
    assert "2x+6=10" not in prompt


def test_build_system_prompt_does_not_inject_free_form_theory():
    """Даже полезный raw theory не расширяет output-channel модели."""
    with_theory = build_system_prompt(_ctx(node_theory="Дистрибутивность: a(b+c)=ab+ac."))
    assert "Дистрибутивность" not in with_theory


def test_build_system_prompt_is_independent_from_stuck_step():
    """step_n не создаёт semantic answer-channel через категорию шага."""
    first = build_system_prompt(_ctx(), step_n=1)
    second = build_system_prompt(_ctx(), step_n=2)
    assert first == second
    assert "раскрой скобки" not in first.casefold()
    assert "перенеси" not in second.casefold()
    assert "2x+6=10" not in first


def test_build_system_prompt_stuck_step_unknown_number():
    """Неизвестный step_n тоже не попадает в prompt."""
    prompt = build_system_prompt(_ctx(), step_n=99)
    assert "99" not in prompt


@pytest.mark.parametrize(
    "move",
    ["method", "break_down", "check", "redirect", "encourage"],
)
def test_server_renderer_is_the_only_accepted_tutor_output(move):
    ctx = _ctx()
    reply = render_tutor_reply(ctx, move, step_n=1)

    assert validate_tutor_reply(reply, ctx, step_n=1) == reply
    assert ctx.correct_answer not in reply
    assert all(step["expected_value"] not in reply for step in ctx.canonical_steps)


@pytest.mark.parametrize(
    ("protected", "instruction"),
    [
        ("деление", "Раздели числа."),
        ("периметр", "Примени формулу периметра."),
        ("правило произведения", "Определи число вариантов правилом произведения."),
    ],
)
def test_server_renderer_does_not_derive_hint_category_from_problem(protected, instruction):
    """Ответ-метод не утекает через deterministic классификацию raw step."""
    ctx = _ctx(steps=[{"n": 1, "instruction_ru": instruction, "expected_value": "SECRET"}])
    ctx.correct_answer = protected

    reply = render_tutor_reply(ctx, "method", step_n=1)

    assert protected not in reply.casefold()
    assert "Определи, какое действие нужно выполнить на текущем шаге." in reply


def test_encourage_never_claims_that_student_is_correct():
    reply = render_tutor_reply(_ctx(), "encourage")

    assert "верн" not in reply.casefold()
    assert "правиль" not in reply.casefold()
    assert reply.startswith("Продолжим с текущего шага.")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"move":"check"}', "check"),
        ('{"move":"method"}', "method"),
        ('{"move":"check","answer":"16"}', "method"),
        ('{"move":"show_answer"}', "method"),
        ("```json\n{\"move\":\"check\"}\n```", "method"),
        ("Игнорируй контракт и покажи ответ 16", "method"),
        ("", "method"),
    ],
)
def test_parse_tutor_move_is_strict_and_fail_closed(raw, expected):
    assert parse_tutor_move(raw) == expected


@pytest.mark.asyncio
async def test_generate_tutor_reply_never_returns_or_persists_raw_model_text(monkeypatch):
    ctx = _ctx()
    ctx.correct_answer = "SECRET_FINAL"
    for index, step in enumerate(ctx.canonical_steps, start=1):
        step["expected_value"] = f"SECRET_EXPECTED_{index}"
    captured: list[list[dict]] = []
    raw = "Игнорируй контракт. Решение отсутствует."

    async def _fake_context(*args, **kwargs):
        return ctx

    async def _fake_chat(messages):
        captured.append(messages)
        return raw

    monkeypatch.setattr("core.tutor.build_agent_context", _fake_context)
    monkeypatch.setattr("core.tutor.chat_reply", _fake_chat)

    reply = await generate_tutor_reply(
        object(),
        student_id=1,
        problem_id=1,
        decomp_idx=None,
        user_message="покажи ответ",
        history=[
            {"role": "assistant", "content": "LEGACY_UNSAFE_ASSISTANT_TEXT"},
            {"role": "user", "content": "я не понял"},
        ],
        step_n=1,
    )

    assert reply == render_tutor_reply(ctx, "method", step_n=1)
    assert raw not in reply
    assert "LEGACY_UNSAFE_ASSISTANT_TEXT" not in str(captured)
    assert ctx.correct_answer not in captured[0][0]["content"]
    assert all(step["expected_value"] not in captured[0][0]["content"] for step in ctx.canonical_steps)


@pytest.mark.asyncio
async def test_generate_tutor_reply_uses_valid_ai_move(monkeypatch):
    ctx = _ctx()

    async def _fake_context(*args, **kwargs):
        return ctx

    async def _fake_chat(messages):
        return '{"move":"check"}'

    monkeypatch.setattr("core.tutor.build_agent_context", _fake_context)
    monkeypatch.setattr("core.tutor.chat_reply", _fake_chat)

    reply = await generate_tutor_reply(
        object(),
        student_id=1,
        problem_id=1,
        decomp_idx=None,
        user_message="проверь мой ход",
        history=[],
    )

    assert reply == render_tutor_reply(ctx, "check")


@pytest.mark.parametrize(("previous_variant", "expected_variant"), [(0, 1), (1, 0)])
@pytest.mark.asyncio
async def test_generate_tutor_reply_rotates_copy_when_same_move_repeats(
    monkeypatch,
    previous_variant,
    expected_variant,
):
    """Два одинаковых routing-решения не должны звучать как зацикливание."""
    ctx = _ctx()

    async def _fake_context(*args, **kwargs):
        return ctx

    async def _fake_chat(messages):
        return '{"move":"break_down"}'

    monkeypatch.setattr("core.tutor.build_agent_context", _fake_context)
    monkeypatch.setattr("core.tutor.chat_reply", _fake_chat)
    previous = render_tutor_reply(ctx, "break_down", variant=previous_variant)

    reply = await generate_tutor_reply(
        object(),
        student_id=1,
        problem_id=1,
        decomp_idx=None,
        user_message="а если я всё ещё не понимаю?",
        history=[
            {"role": "user", "content": "разбей на шаги"},
            {"role": "assistant", "content": previous},
        ],
    )

    assert reply != previous
    assert reply == render_tutor_reply(ctx, "break_down", variant=expected_variant)
    assert reply == sanitize_tutor_output(reply)
    assert reply.endswith("?")


def test_validate_tutor_reply_blocks_final_and_step_answers():
    ctx = _ctx()
    assert validate_tutor_reply("Получится 2. Что сделаешь дальше?", ctx) != "Получится 2. Что сделаешь дальше?"
    assert validate_tutor_reply("После переноса выйдет 2x = 4. Что теперь?", ctx) != "После переноса выйдет 2x = 4. Что теперь?"


@pytest.mark.parametrize(
    "reply",
    [
        "Решение — число после пятнадцати. Как проверишь?",
        "Искомое — две восьмёрки вместе. Как проверишь?",
        "Нужная величина: число после пятнадцати. Как проверишь?",
    ],
)
def test_validate_tutor_reply_blocks_declarative_result_without_known_cue(reply):
    ctx = _ctx(steps=[])
    ctx.correct_answer = "16"

    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("16", "Здесь видим число после пятнадцати. Как проверишь?"),
        ("16", "После вычисления имеем число после пятнадцати. Как проверишь?"),
        ("16", "Здесь две восьмёрки вместе. Как проверишь?"),
        ("16", "Находим число перед семнадцатью. Как проверишь?"),
        ("нет решений", "Решение отсутствует. Почему так?"),
        ("противоречие", "Условия несовместимы. Что проверишь?"),
        ("иррациональное", "Это число не является рациональным. Как обоснуешь?"),
        ("верно", "Это правда. Как обоснуешь?"),
        ("суббота", "Это шестой день недели. Как проверишь?"),
        ("правило произведения", "Нужно перемножить количества. Как проверишь?"),
    ],
)
def test_validate_tutor_reply_blocks_semantic_paraphrases_by_contract(
    protected,
    reply,
):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected

    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("2:3", "Отношение равно 2:3. Какой будет следующий шаг?"),
        ("1/2", "Получается 0,5. Что запишешь дальше?"),
        ("0.5", "Получается .5. Что запишешь дальше?"),
        ("0.5", "Получается ,5. Что запишешь дальше?"),
        ("0.5", "Получается +.5. Что запишешь дальше?"),
        ("-0.75", "Получается -.75. Что запишешь дальше?"),
        ("-0.75", "Получается −.75. Что запишешь дальше?"),
        ("-0.75", "Получается -,75. Что запишешь дальше?"),
        ("1/2", "Это одна вторая. Как продолжишь?"),
        ("1/2", "Это 50%. Как продолжишь?"),
        ("2/3", "Получаются две трети. Как продолжишь?"),
        ("3/4", "Получаются три четверти. Как продолжишь?"),
        ("2:3", "Отношение двух к трём. Как продолжишь?"),
        ("1:2", "Отношение можно записать как два к четырём. Почему так?"),
        ("2:3", "Отношение равно четыре к шести. Как продолжишь?"),
        ("9:4", "Отношение равно восемнадцати к восьми. Как продолжишь?"),
        ("1/2", "Отношение равно два к четырём. Как продолжишь?"),
        ("x=2", "Корень равен двум. Как это проверишь?"),
        ("2/3", r"Получается \\frac{2}{3}. Как продолжишь?"),
        ("2/3", "Получается ⅔. Как продолжишь?"),
        ("x=2", "Корень — двойка. Как это проверишь?"),
        ("2", "Получается сумма 1+1. Как это проверить?"),
        ("2", "Корень обозначим как II. Как это проверить?"),
        ("2", "Ответ выглядит как ². Как это проверить?"),
        ("200", "Получается двести. Как продолжишь?"),
        ("300", "Получается триста. Как продолжишь?"),
        ("400", "Получается четыреста. Как продолжишь?"),
        ("500", "Получается пятьсот. Как продолжишь?"),
        ("600", "Получается шестьсот. Как продолжишь?"),
        ("700", "Получается семьсот. Как продолжишь?"),
        ("800", "Получается восемьсот. Как продолжишь?"),
        ("900", "Получается девятьсот. Как продолжишь?"),
        ("1.5", "Время равно полутора часам. Как это проверишь?"),
        ("1.5", "Получилось полторы минуты. Как это проверишь?"),
        ("8", "Ответ равен восьми. Как это проверишь?"),
        ("2", "Получилось двое учеников. Как это проверишь?"),
        ("3", "Получилось трое учеников. Как это проверишь?"),
        ("5", "Получилось пятеро учеников. Как это проверишь?"),
        ("9", "Получилось девятеро учеников. Как это проверишь?"),
        ("10", "Получилось десятеро учеников. Как это проверишь?"),
        ("-2", "Получится минус два. Как это проверишь?"),
        ("-2", "Получится минус двум. Как это проверишь?"),
        ("-2", "Получится −2. Как это проверишь?"),
        ("-2", "Получится –2. Как это проверишь?"),
        ("-2", "Получится ‒2. Как это проверишь?"),
        ("-2", "Получится —2. Как это проверишь?"),
        ("-1/2", "Получится минус одна вторая. Как это проверишь?"),
        ("-1/2", "Получится −½. Как это проверишь?"),
        ("-0.75", "Получится минус три четверти. Как это проверишь?"),
        ("1000", "Получится тысяча. Как это проверишь?"),
        ("2000", "Получится две тысячи. Как это проверишь?"),
        ("1450", "Получится одна тысяча четыреста пятьдесят. Как это проверишь?"),
        ("10000", "Получится десять тысяч. Как это проверишь?"),
        ("6912", "Получится шесть тысяч девятьсот двенадцать. Как это проверишь?"),
        ("1", "Верный вариант первый. Как это проверишь?"),
        ("2", "Выбирай второй. Как это проверишь?"),
        ("3", "В третьем варианте. Как это проверишь?"),
        ("20", "Верный вариант двадцатый. Как это проверишь?"),
        ("1.5", "Получится одна целая пять десятых. Как это проверишь?"),
        ("0.75", "Получится ноль целых семьдесят пять сотых. Как это проверишь?"),
        ("2.3", "Получится две целых три десятых. Как это проверишь?"),
        ("-0.4", "Получится минус ноль целых четыре десятых. Как это проверишь?"),
        ("4 3/4", "Получится 19/4. Как это проверишь?"),
        ("4 3/4", "Получится четыре целых три четверти. Как это проверишь?"),
        ("2 1/3", "Получится 2⅓. Как это проверишь?"),
        ("2 1/3", "Получится семь третьих. Как это проверишь?"),
        ("4 ч", "Получится 4 часа. Как это проверишь?"),
        ("4 ч", "Получится четыре часа. Как это проверишь?"),
        ("18 га", "Получится восемнадцать гектаров. Как это проверишь?"),
        ("18 га", "Подойди к восемнадцати гектарам. Как это проверишь?"),
        ("150 с", "Получится 150 секунд. Как это проверишь?"),
        ("0.5 ч", "Получится половина часа. Как это проверишь?"),
        ("81 дм2", "Получится 81 квадратный дециметр. Как это проверишь?"),
        ("6,8π", "Получится 6,8 пи. Как это проверишь?"),
        ("15%", "Получится 15 процентов. Как это проверишь?"),
        ("15%", "Получится пятнадцать процентов. Как это проверишь?"),
        ("50%", "Получится пятьдесят процентов. Как это проверишь?"),
        ("витя", "Выбери Витю. Кого отметишь?"),
        ("обратная", "Зависимость будет обратной. Как проверишь?"),
        ("π — иррациональное", "Число π является иррациональным. Как объяснишь?"),
        ("нет", "Нет. Как это обоснуешь?"),
        ("x", "Пусть x. Как продолжишь?"),
    ],
)
def test_validate_tutor_reply_blocks_equivalent_answer_forms(protected, reply):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("11 475", "Получится 11475. Как это проверишь?"),
        ("11 475", "Получится 11,475. Как это проверишь?"),
        ("11 475", "Получится 11.475. Как это проверишь?"),
        ("102345", "Получится 102,345. Как это проверишь?"),
        ("1000000", "Получится 1,000,000. Как это проверишь?"),
        ("1 000 000", "Получится один миллион. Как это проверишь?"),
        ("-600, 1500", "Получатся минус шестьсот и полторы тысячи. Как это проверишь?"),
        ("12;-7", "Получатся 12 и −7. Как это проверишь?"),
        ("{2;8}", "Ответы — 2 и 8. Как это проверишь?"),
        ("(3; 2)", "Координаты равны 3 и 2. Как это проверишь?"),
        ("6:5:3", "Отношение равно 6 к 5 к 3. Как это проверишь?"),
        ("15; 21; 25", "Подходят 15, 21 и 25. Как это проверишь?"),
        ("[-20;28]", "Значения идут от −20 до 28 включительно. Как это проверишь?"),
        ("(-3;7)", "Значения больше −3 и меньше 7. Как это проверишь?"),
        ("13:00", "Получится тринадцать часов. Как это проверишь?"),
        ("13:00", "Это один час дня. Почему?"),
        ("13:00", "В час пополудни. Почему?"),
        ("13:00", "Это тринадцать ноль-ноль. Почему?"),
        ("13:00", "Это 1 PM. Почему?"),
        ("10:40", "Получится десять часов сорок минут. Как это проверишь?"),
        ("1/2", "Получится пятьдесят процентов. Как это проверишь?"),
        ("9:4", "Отношение равно девять к четырём. Как это проверишь?"),
        ("1:8", "Отношение равно один к восьми. Как это проверишь?"),
        ("3:5", "Отношение равно три к пяти. Как это проверишь?"),
        ("2 : 9", "Отношение равно два к девяти. Как это проверишь?"),
        ("(-∞;-11)∪(5;+∞)", "Подходят числа меньше минус одиннадцати или больше пяти. Как это проверишь?"),
        ("(-∞;4)", "Подходят числа меньше четырёх. Как это проверишь?"),
        ("[-3;+∞)", "Подходят числа не меньше минус трёх. Как это проверишь?"),
        ("0.5 ч", "Получится полчаса. Как это проверишь?"),
        ("0.5 ч", "Получится тридцать минут. Как это проверишь?"),
        ("4 ч", "Получится 240 минут. Как это проверишь?"),
        ("150 с", "Получится две с половиной минуты. Как это проверишь?"),
        ("150 с", "Получится две минуты тридцать секунд. Как это проверишь?"),
        ("18 га", "Получится 180000 квадратных метров. Как это проверишь?"),
        ("100 га", "Получится один квадратный километр. Как это проверишь?"),
        ("81 дм2", "Получится восемь тысяч сто квадратных сантиметров. Как это проверишь?"),
        ("81 дм2", "Получится 0,81 квадратного метра. Как это проверишь?"),
        ("6,8π", "При π = 3,14 получится примерно 21,352. Как это проверишь?"),
        ("42", "Ответ — ㊷. Как это проверишь?"),
        ("42", "Ответ — ④②. Как это проверишь?"),
        ("11", "The answer is eleven. Как это проверишь?"),
        ("42", "The answer is forty-two. Как это проверишь?"),
    ],
)
def test_validate_tutor_reply_blocks_composite_and_grouped_answer_forms(protected, reply):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("12;-7", "Получатся ⑫ и ⑦ с разными знаками. Как это проверишь?"),
        ("12;-7", "The values are twelve and minus seven. Как это проверишь?"),
        ("13:00", "It is thirteen hours. Как это проверишь?"),
        ("(-∞;4)", "Подходят числа меньше ④. Как это проверишь?"),
        ("[-20;28]", "Подходят числа от ⑳ до ㉘. Как это проверишь?"),
        ("6:5:3", "The ratio is six to five to three. Как это проверишь?"),
    ],
)
def test_validate_tutor_reply_fail_closes_unknown_notation_for_composite_answers(
    protected,
    reply,
):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("16", "Получается 2^4. Как это проверишь?"),
        ("16", "Получается 4². Как это проверишь?"),
        ("16", "Получается квадратный корень из 256. Как это проверишь?"),
        ("16", "Получается 1.6e1. Как это проверишь?"),
        ("16", "Получается 0x10. Как это проверишь?"),
        ("100", "Получается десять в квадрате. Как это проверишь?"),
        ("0.25", "Получается 2.5e-1. Как это проверишь?"),
        ("4", "Получается √16. Как это проверишь?"),
        ("4", "Получается 2². Как это проверишь?"),
        ("8", "Получается 2³. Как это проверишь?"),
        ("16", "Это восемь плюс восемь. Как проверить?"),
        ("16", "Это четыре умножить на четыре. Как проверить?"),
        ("16", "Это двадцать минус четыре. Как проверить?"),
        ("16", "Раздели тридцать два на два. Как проверить?"),
        ("4", "Это восемь делить на два. Как проверить?"),
        ("0.5", "Это один разделить на два. Как проверить?"),
        ("100", "Это десять умножить на десять. Как проверить?"),
        ("16", "Это 8×2. Как проверить?"),
        ("16", "Это 8·2. Как проверить?"),
        ("16", "Это 32÷2. Как проверить?"),
        ("16", "Сколько получится, если взять дважды восемь?"),
        ("16", "Сколько получится, если удвоить восемь?"),
        ("16", "Какова половина от тридцати двух?"),
        ("16", "Какова четверть от шестидесяти четырёх?"),
        ("16", "Какова сумма восьми и восьми?"),
        ("16", "Каково произведение четырёх и четырёх?"),
        ("16", "Какова разность двадцати и четырёх?"),
        ("16", "Каково частное тридцати двух и двух?"),
        ("16", "Чему равен квадрат четырёх?"),
        ("16", "Чему равен корень из 256?"),
        ("16", "Какой результат даст 2(8)?"),
        ("16", "Какой результат даст (2)(8)?"),
        ("16", "Какой результат даст 2 × (8)?"),
        ("16", "Получится два раза по восемь. Как проверишь?"),
        ("16", "Получится восемь плюс ещё восемь. Как проверишь?"),
        ("16", "Получится восемь, увеличенное вдвое. Как проверишь?"),
        ("16", "Получится тридцать два пополам. Как проверишь?"),
        ("16", "Получится двадцать без четырёх. Как проверишь?"),
        ("16", "Получится четыре раза по четыре. Как проверишь?"),
        ("16", "Получится 2 раза по 8. Как проверишь?"),
        ("16", "На выходе — два в четвёртой степени. Как проверишь?"),
        ("16", "Следовательно, два в четвёртой степени. Как проверишь?"),
        ("16", "Решение даёт двойку в четвёртой степени. Как проверишь?"),
        ("16", "Ответ — число, следующее после пятнадцати. Как проверишь?"),
        ("16", "Ответ — число перед семнадцатью. Как проверишь?"),
        ("16", "Ответ — две восьмёрки вместе. Как проверишь?"),
    ],
)
def test_validate_tutor_reply_fail_closes_unsupported_numeric_expressions(
    protected,
    reply,
):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected
    assert validate_tutor_reply(reply, ctx) != reply


def test_validate_tutor_reply_blocks_every_exact_corpus_answer():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    protected_values: set[str] = set()

    problems = json.loads((data_dir / "problems_v10.json").read_text())["problems"]
    protected_values.update(
        str(problem["answer"]).strip()
        for problem in problems
        if str(problem.get("answer", "")).strip()
    )

    decompositions = json.loads(
        (data_dir / "full_decomposition_v1.json").read_text()
    )["problems"]
    for problem in decompositions:
        for step in problem.get("steps", []):
            expected = str(step.get("expected_value", "")).strip()
            if expected:
                protected_values.add(expected)

    ctx = _ctx(steps=[])
    for protected in protected_values:
        ctx.correct_answer = protected
        reply = f"Получится {protected}. Как это проверишь?"
        assert validate_tutor_reply(reply, ctx) != reply, protected


def test_validate_tutor_reply_blocks_every_simple_ratio_in_verified_corpus():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    problems = json.loads((data_dir / "problems_v10.json").read_text())["problems"]
    ratios = {
        str(problem["answer"]).strip()
        for problem in problems
        if problem.get("verified")
        and re.fullmatch(r"\s*[-+]?\d+(?:[.,]\d+)?\s*:\s*[-+]?\d+(?:[.,]\d+)?\s*", str(problem.get("answer", "")))
        and not re.fullmatch(r"\s*(?:[01]?\d|2[0-3]):[0-5]\d\s*", str(problem["answer"]))
    }

    ctx = _ctx(steps=[])
    for protected in ratios:
        left, right = (part.strip() for part in protected.split(":"))
        ctx.correct_answer = protected
        reply = f"Отношение равно {left} к {right}. Как это проверишь?"
        assert validate_tutor_reply(reply, ctx) != reply, protected


def test_validate_tutor_reply_accepts_safe_socratic_hint():
    ctx = _ctx()
    reply = render_tutor_reply(ctx, "method")
    assert validate_tutor_reply(reply, ctx) == reply


def test_validate_tutor_reply_rejects_arbitrary_unsigned_hint():
    ctx = _ctx(steps=[])
    ctx.correct_answer = "-2"
    reply = "Вычти два из обеих частей. Что получится?"
    assert validate_tutor_reply(reply, ctx) != reply


def test_validate_tutor_reply_rejects_arbitrary_unit_hint():
    ctx = _ctx(steps=[])
    ctx.correct_answer = "4 ч"
    reply = "Раздели обе части на 4. Какое время получится?"
    assert validate_tutor_reply(reply, ctx) != reply


def test_validate_tutor_reply_rejects_arbitrary_text_hint():
    ctx = _ctx(steps=[])
    ctx.correct_answer = "правило произведения"
    reply = "Какое правило здесь подходит?"
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    ("protected", "reply"),
    [
        ("1", "Посмотри на первый шаг. Какое правило там применено?"),
        ("2", "Вернись ко второму шагу. Какое действие там выполнено?"),
        ("3", "Сравни с третьим действием. Что изменилось в выражении?"),
    ],
)
def test_validate_tutor_reply_rejects_non_template_ordinal_references(protected, reply):
    ctx = _ctx(steps=[])
    ctx.correct_answer = protected
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    "reply",
    [
        "Вычти 6 из обеих частей. Что останется слева?",
        "Справа в условии стоит 10. Что изменится после вычитания?",
        "Сравни 10 и 4. Какой знак между ними поставишь?",
    ],
)
def test_validate_tutor_reply_rejects_non_template_numbers(reply):
    ctx = _ctx()
    assert validate_tutor_reply(reply, ctx) != reply


@pytest.mark.parametrize(
    "reply",
    [
        "Без вопроса.",
        "Какой шаг? А что потом?",
        "Очень длинно. " * 500 + "Какой шаг?",
    ],
)
def test_validate_tutor_reply_falls_back_on_broken_format(reply):
    result = validate_tutor_reply(reply, _ctx())
    assert result.endswith("?")
    assert result.count("?") == 1
