"""Контент-гейт детских инструкций шага."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.step_content import (
    instruction_reveals_protected_value,
    safe_step_instruction,
)


@pytest.mark.parametrize(
    ("instruction", "expected", "answer", "safe_fragment"),
    [
        ("Посчитай: 29 + 7 = 36 яблок.", "36", "36", "29 + 7"),
        ("Раздели 4056 на 12: частное равно 338.", "338", "338", "Раздели 4056 на 12"),
        ("Возведи 2 в шестую степень: 2⁶ = 64.", "64", "91", "2⁶"),
        ("Назови цифру в разряде сотен: это 2.", "2", "2", "разряде сотен"),
        ("Вычисли 10! = 3628800.", "3628800", "8", "10!"),
    ],
)
def test_safe_step_instruction_removes_result_but_keeps_action(
    instruction,
    expected,
    answer,
    safe_fragment,
):
    safe = safe_step_instruction(
        instruction,
        expected_value=expected,
        correct_answer=answer,
    )

    assert safe_fragment in safe
    assert not instruction_reveals_protected_value(safe, [expected, answer])


def test_safe_step_instruction_keeps_operand_equal_to_expected():
    instruction = "Раздели 144 на 12."
    assert safe_step_instruction(
        instruction,
        expected_value="12",
        correct_answer="12",
    ) == instruction


@pytest.mark.parametrize(
    ("problem_idx", "step_n", "safe_fragment", "forbidden_fragment"),
    [
        (120, 2, "Сравни дроби", "3/5 > 2/5"),
        (121, 2, "Сравни дроби", "1/3 > 1/4"),
        (154, 3, "Сложи числа", "остаётся 3/4"),
        (220, 4, "Найди нужный знаменатель", "равен 20"),
        (225, 2, "Определи период", "цифра 6"),
        (239, 3, "Найди наименьшее", "12 — наименьшее"),
        (254, 1, "Попробуй подобрать", "3 и 97"),
        (705, 1, "количество допустимых вариантов", "4 варианта"),
        (717, 1, "количество допустимых вариантов", "9 вариантов"),
        (55, 2, "Найди наименьшее", "— 1450"),
        (199, 1, "Найди ближайшую", ": 2.3"),
        (233, 3, "Посчитай делители", "их 6"),
        (250, 1, "выпиши простые", "2, 3, 5, 7, 11, 13, 17, 19"),
        (1354, 2, "Посчитай", "их 6"),
        (1843, 4, "Запиши целые числа", "Их 3"),
        (2520, 4, "Сложи последние цифры", "суммы — 1"),
        (687, 1, "Определи нужную координату", "первое число — 3"),
    ],
)
def test_known_corpus_result_sentences_become_meaningful_actions(
    problem_idx,
    step_n,
    safe_fragment,
    forbidden_fragment,
):
    """Независимый regression: проверяем конкретный UX-текст, не detector."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "full_decomposition_v1.json"
    problems = json.loads(data_path.read_text(encoding="utf-8"))["problems"]
    problem = next(item for item in problems if item.get("idx") == problem_idx)
    step = next(item for item in problem["steps"] if item.get("n") == step_n)

    safe = safe_step_instruction(
        step["instruction_ru"],
        expected_value=step["expected_value"],
        correct_answer=problem.get("answer"),
    )

    assert safe_fragment in safe
    assert forbidden_fragment not in safe


def test_every_corpus_step_is_safe_at_publish_boundary():
    data_path = Path(__file__).resolve().parents[1] / "data" / "full_decomposition_v1.json"
    problems = json.loads(data_path.read_text(encoding="utf-8"))["problems"]

    for problem in problems:
        final_answer = problem.get("answer")
        for step in problem.get("steps", []):
            safe = safe_step_instruction(
                step["instruction_ru"],
                expected_value=step["expected_value"],
                correct_answer=final_answer,
            )
            assert safe.strip(), (problem.get("idx"), step.get("n"))
            assert not instruction_reveals_protected_value(
                safe,
                [step["expected_value"], final_answer],
            ), (problem.get("idx"), step.get("n"), safe)
