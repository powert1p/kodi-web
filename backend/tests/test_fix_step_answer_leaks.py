"""Table-driven тесты для clean_instruction (backend/scripts/fix_step_answer_leaks.py).

Чистая функция, БД не нужна — юнит-тесты без db_session-фикстуры.
"""

import sys
from pathlib import Path

# scripts/ не пакет — добавляем в sys.path, как и остальные backend-модули в тестах.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fix_step_answer_leaks import clean_instruction  # noqa: E402


# ── Случаи, где хвост "= <ev>" СРЕЗАЕТСЯ ──

CUT_CASES = [
    # (instruction_ru, expected_value, ожидаемый результат)
    ("Сначала сложи: 63 + 28 = 91.", "91", "Сначала сложи: 63 + 28."),
    ("Всего шаров: 58 ÷ 2 = 29", "29", "Всего шаров: 58 ÷ 2"),
    ("11x = 11 · 24 = 264.", "264", "11x = 11 · 24."),
]

# ── Случаи, где правка НЕ применяется (None) ──

NO_CUT_CASES = [
    ("x = 1.", "1"),                                  # одиночная переменная, нет оператора перед "="
    ("29 + 7 = 36 яблок.", "36"),                      # mid-sentence, "= ev" не в конце строки
    ("99 × 15 = (100 − 1) × 15", "(100 − 1) × 15"),    # ev не числовой (скобки/оператор внутри)
    ("Ответ: 2⁹.", "2⁹"),                               # ev не числовой (степень с superscript)
    ("Частное равно 338.", "338"),                     # нет "=" вообще в тексте
]


def test_cut_cases():
    for instr, ev, expected in CUT_CASES:
        assert clean_instruction(instr, ev) == expected, f"instr={instr!r} ev={ev!r}"


def test_no_cut_cases():
    for instr, ev in NO_CUT_CASES:
        assert clean_instruction(instr, ev) is None, f"instr={instr!r} ev={ev!r}"


def test_idempotent():
    """Повторное применение clean_instruction к уже очищенному тексту — без изменений (None)."""
    for instr, ev, expected in CUT_CASES:
        cleaned = clean_instruction(instr, ev)
        assert cleaned == expected
        assert clean_instruction(cleaned, ev) is None, (
            f"повторная правка не идемпотентна: {cleaned!r} (ev={ev!r})"
        )
