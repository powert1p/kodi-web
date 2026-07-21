"""Безопасная публикация инструкций шагов декомпозиции.

Банк хранит авторские объяснения, часть которых исторически содержит уже
вычисленный ``expected_value``. Внутри AI-grounding полный текст допустим, но в
детский клиент должна уходить постановка действия без готового результата.
"""

from __future__ import annotations

import re
from typing import Iterable, TypedDict


_RESULT_CUE_RE = re.compile(
    r"(?:"
    r"[=≈→]|"
    r"(?<!\w)(?:"
    r"то\s+есть|"
    r"равн\w*|равен|получ\w*|ответ\w*|результат\w*|итог\w*|"
    r"состав\w*|будет|да[её]т|значит|это|"
    r"оста(?:ток|лось|нется|[её]тся)\w*|выходит|подходит|стоит|"
    r"например|всего|их|(?:больш|меньш)\w*\s+дроб\w*|то"
    r")(?!\w)"
    r")",
    re.IGNORECASE,
)
_ACTION_WITH_VALUE_RE = re.compile(
    r"(?<!\w)(?:запиши|назови|возьми|выбери|укажи|получи)\w*(?!\w)",
    re.IGNORECASE,
)
_ACTION_VERB_RE = re.compile(
    r"(?<!\w)(?:"
    r"вычисли|найди|посчитай|раздели|подели|умножь|помножь|перемножь|"
    r"возведи|сложи|"
    r"прибавь|добавь|вычти|отними|сравни|запиши|назови|возьми|"
    r"выбери|укажи|округли|приведи|раскрой|перенеси|сократи|"
    r"подставь|замени|разложи|вынеси|попробуй|проверь|определи|"
    r"преобразуй|представь|составь|реши|переведи|перебери|заметь"
    r")\w*(?!\w)",
    re.IGNORECASE,
)
_STEP_OPERAND_RE = re.compile(
    r"(?<!\w)шаг\s*\d*\s*:\s*[^.!?]*[+−–×·∙÷*]",
    re.IGNORECASE,
)
_SPACE_RE = re.compile(r"\s+")
_SIMPLE_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:\s*%)?")
_FRACTION_RE = re.compile(r"[-+]?\d+\s*/\s*\d+")
_MIXED_FRACTION_RE = re.compile(r"[-+]?\d+\s+\d+\s*/\s*\d+")
_UNIT_VALUE_RE = re.compile(
    r"[-+]?\d+(?:[.,]\d+)?(?:\s+\d+\s*/\s*\d+)?\s*[A-Za-zА-Яа-яЁё²³/%]+"
)
_EXPRESSION_MARKER_RE = re.compile(r"[=+−–×·∙÷*^()]|[A-Za-zА-Яа-яЁё]\s*=")


class GuidedInputContract(TypedDict):
    """Публичная подсказка о форме ответа без раскрытия expected value."""

    prompt: str
    format_hint: str
    example: str
    input_mode: str


def _value_pattern(value: object) -> re.Pattern[str] | None:
    raw = str(value).strip()
    if not raw:
        return None

    if _SIMPLE_NUMBER_RE.fullmatch(raw):
        number = re.escape(raw).replace(r"\,", "[.,]").replace(r"\.", "[.,]")
        return re.compile(rf"(?<![\w\d]){number}(?![\w\d])", re.IGNORECASE)

    # Для выражений и списков разрешаем различия только в пробелах. Это ловит
    # ``2⁹·(2−1)`` против ``2⁹ · (2 − 1)``, не превращая короткий ответ ``1``
    # в совпадение с ``100``.
    parts = [re.escape(part) for part in _SPACE_RE.split(raw) if part]
    if not parts:
        return None
    return re.compile(r"\s*".join(parts), re.IGNORECASE)


def _protected_spans(text: str, values: Iterable[object]) -> list[tuple[int, int]]:
    spans: set[tuple[int, int]] = set()
    for value in values:
        pattern = _value_pattern(value)
        if pattern is None:
            continue
        spans.update((match.start(), match.end()) for match in pattern.finditer(text))
    return sorted(spans)


def _reveal_cut(text: str, values: Iterable[object]) -> int | None:
    """Находит границу, после которой инструкция раскрывает protected value."""
    value_spans = _protected_spans(text, values)
    if not value_spans:
        return None

    stripped = text.strip().rstrip(".!?")
    if any(start == text.find(stripped) and end >= text.find(stripped) + len(stripped)
           for start, end in value_spans):
        return 0

    cues = list(_RESULT_CUE_RE.finditer(text)) + list(_ACTION_WITH_VALUE_RE.finditer(text))
    best: tuple[int, int] | None = None
    for value_start, _value_end in value_spans:
        sentence_start = max(
            text.rfind(".", 0, value_start),
            text.rfind("!", 0, value_start),
            text.rfind("?", 0, value_start),
        ) + 1
        sentence_ends = [
            end for mark in ".!?"
            if (end := text.find(mark, _value_end)) >= 0
        ]
        sentence_end = min(sentence_ends) if sentence_ends else len(text)
        sentence = text[sentence_start:sentence_end]
        value_offset = value_start - sentence_start

        # Готовый ответ иногда начинает отдельную фразу: ``12 — наименьшее``.
        before = text[sentence_start:value_start]
        after = text[_value_end:_value_end + 48]
        if not before.strip() and re.match(
            r"\s*(?:[—–-]|(?:явля\w*|это|будет|подходит)\b)",
            after,
            re.IGNORECASE,
        ):
            leading_candidate = (0, sentence_start)
            if best is None or leading_candidate < best:
                best = leading_candidate

        # Двоеточие после команды часто отделяет уже готовый результат:
        # ``Посчитай делители: их 6``. Арифметический операнд после маркировки
        # шага (``Шаг 1: 180 ÷ 6``) остаётся допустимым.
        colon_offset = sentence.rfind(":", 0, value_offset)
        if colon_offset >= 0:
            suffix = sentence[colon_offset + 1:]
            before_value = sentence[colon_offset + 1:value_offset]
            is_operand_expression = (
                _STEP_OPERAND_RE.search(sentence) is not None
                or re.search(r"[=≈→]", before_value) is not None
                or (
                    re.search(r"[+−–×·∙÷*]", suffix) is not None
                    and re.search(r"[=≈→<>≤≥]", suffix) is None
                )
            )
            if not is_operand_expression:
                colon_candidate = (0, sentence_start + colon_offset)
                if best is None or colon_candidate < best:
                    best = colon_candidate

        # Cue из предыдущей фразы не относится к текущему protected value.
        # Иначе ``это`` в первой фразе маскировало декларативный ответ после
        # точки: ``... . Первое число — 3``.
        preceding = [
            cue
            for cue in cues
            if sentence_start < cue.end() <= value_start
        ]
        if not preceding:
            # Декларативная фраза с protected value — это объяснение результата,
            # а не задание ребёнку. Исключение — явное действие или маркированный
            # арифметический операнд ``Шаг 1: 180 ÷ 6``.
            if not (
                _ACTION_VERB_RE.search(sentence[:value_offset]) is not None
                or _STEP_OPERAND_RE.search(sentence) is not None
            ):
                declarative_candidate = (0, sentence_start)
                if best is None or declarative_candidate < best:
                    best = declarative_candidate
            continue
        cue = max(preceding, key=lambda item: item.end())
        between = text[cue.end():value_start]
        # Защитный fail-close на случай нестандартной пунктуации внутри
        # выделенной фразы. Точка в десятичной записи находится внутри span.
        if re.search(r"[.!?]\s+", between):
            if not (
                _ACTION_VERB_RE.search(sentence[:value_offset]) is not None
                or _STEP_OPERAND_RE.search(sentence) is not None
            ):
                declarative_candidate = (0, sentence_start)
                if best is None or declarative_candidate < best:
                    best = declarative_candidate
            continue
        distance = value_start - cue.end()
        if distance > 120:
            continue
        candidate = (distance, cue.start())
        if best is None or candidate < best:
            best = candidate

    return None if best is None else best[1]


def instruction_reveals_protected_value(
    instruction: str,
    protected_values: Iterable[object],
) -> bool:
    """Проверяет именно выдачу результата, не блокируя операнды задания."""
    return _reveal_cut(instruction, protected_values) is not None


def _fallback_instruction(source: str) -> str:
    folded = source.casefold().replace("ё", "е")
    if "период" in folded or "повторяется бесконечно" in folded:
        return "Определи период десятичной дроби и запиши его."
    if "прост" in folded and "числ" in folded:
        return "Выпиши простые числа из указанного диапазона."
    if "ближайш" in folded and "десятичн" in folded:
        return "Найди ближайшую десятичную дробь с нужной стороны."
    if "наименьш" in folded and "числ" in folded:
        return "Найди наименьшее число, удовлетворяющее условию."
    if "координат" in folded or "абсцисс" in folded or "ординат" in folded:
        return "Определи нужную координату точки и запиши её."
    if "знаменател" in folded:
        return "Найди нужный знаменатель и запиши его."
    if "делител" in folded and "числ" in folded:
        return "Найди число с указанным количеством делителей и запиши его."
    if "вариант" in folded or "можно выбрать" in folded:
        return "Определи количество допустимых вариантов для этого шага."
    if ("больш" in folded or "меньш" in folded) and "дроб" in folded:
        return "Сравни дроби по указанному правилу и запиши ответ."
    if "нок" in folded:
        return "Найди наименьшее общее кратное и запиши его."
    if "нод" in folded:
        return "Найди наибольший общий делитель и запиши его."
    if "делимост" in folded or "нацело дел" in folded:
        return "Проверь признак делимости и запиши вывод."
    if "уравнен" in folded or "обознач" in folded or "неизвестн" in folded:
        return "Составь уравнение для этого шага и реши его."
    if "неравен" in folded:
        return "Преобразуй неравенство и запиши множество решений."
    if "вероятност" in folded or "благоприятн" in folded:
        return "Найди отношение благоприятных исходов ко всем исходам."
    if "масштаб" in folded:
        return "Примени масштаб и найди требуемую величину."
    if "процент" in folded or "%" in source:
        return "Переведи проценты в долю и выполни действие этого шага."
    if "площад" in folded:
        return "Примени формулу площади и запиши результат."
    if "периметр" in folded:
        return "Примени формулу периметра и запиши результат."
    if "объем" in folded or "объём" in source.casefold():
        return "Примени формулу объёма и запиши результат."
    if "скорост" in folded:
        return "Используй связь пути, скорости и времени для этого шага."
    if "разряд" in folded or "цифр" in folded or "запят" in folded:
        return "Определи нужную цифру или разряд и запиши ответ."
    if "модул" in folded:
        return "Примени определение модуля и запиши результат."
    if "последовательност" in folded or "следующ" in folded:
        return "Найди закономерность последовательности и продолжи её."
    if "округ" in folded:
        return "Округли указанное число до нужного разряда и запиши результат."
    if any(word in folded for word in ("раздел", "частн", "подел")) or "÷" in source:
        return "Выполни деление этого шага и запиши результат."
    if any(word in folded for word in ("слож", "сумм", "прибав")):
        return "Выполни сложение этого шага и запиши результат."
    if "+" in source and "−" in source:
        return "Сложи числа с учётом их знаков и запиши результат."
    if any(word in folded for word in ("выч", "разност", "отним")):
        return "Выполни вычитание этого шага и запиши результат."
    if any(word in folded for word in ("умнож", "перемнож", "произвед", "стоимост")):
        return "Выполни умножение этого шага и запиши результат."
    if any(word in folded for word in ("сосчитай", "посчитай", "количеств", "сколько")):
        return "Сосчитай требуемое количество и запиши результат."
    if any(symbol in source for symbol in ("+", "−", "×", "·", "÷", "=")):
        return "Вычисли значение выражения этого шага и запиши результат."
    if any(word in folded for word in ("степен", "квадрат", "куб", "факториал")):
        return "Вычисли значение выражения этого шага и запиши результат."
    if "остат" in folded:
        return "Найди остаток этого шага и запиши его."
    if "сравн" in folded:
        return "Сравни значения по правилу этого шага и запиши вывод."
    if "скоб" in folded:
        return "Раскрой скобки по правилу и упрости выражение."
    if "перенес" in folded or "перенеси" in folded:
        return "Перенеси слагаемое в другую часть и учти смену знака."
    return "Выполни действие этого шага и запиши промежуточный результат."


def safe_step_action(source: str) -> str:
    """Возвращает value-free действие из конечного серверного словаря.

    В отличие от ``safe_step_instruction`` функция никогда не переносит в
    результат фрагменты исходного текста. Это граница для AI-тьютора: модель
    может выбрать сценарий помощи, но child-visible формулировка строится только
    сервером и не наследует semantic paraphrase готового ответа.
    """
    normalised = _SPACE_RE.sub(" ", source).strip()
    return _fallback_instruction(normalised)


def guided_input_contract(
    instruction: str,
    *,
    expected_value: object,
) -> GuidedInputContract:
    """Объясняет ребёнку, что вводить на текущем шаге.

    Все примеры намеренно синтетические и не строятся из ``expected_value``.
    Неизвестная или неполная форма всегда получает безопасный текстовый fallback.
    """

    source = _SPACE_RE.sub(" ", str(instruction)).strip()
    expected = _SPACE_RE.sub(" ", str(expected_value)).strip()
    folded = source.casefold().replace("ё", "е")

    if (
        "отношени" in folded
        and any(word in folded for word in ("част", "сумм", "всего"))
    ):
        return {
            "prompt": "Запиши действие, которое нужно выполнить на этом шаге.",
            "format_hint": "Например: 2 + 3 + 4",
            "example": "2 + 3 + 4",
            "input_mode": "text",
        }
    if _MIXED_FRACTION_RE.fullmatch(expected):
        return {
            "prompt": "Запиши смешанное число.",
            "format_hint": "Например: 2 1/3",
            "example": "2 1/3",
            "input_mode": "text",
        }
    if _FRACTION_RE.fullmatch(expected):
        return {
            "prompt": "Запиши дробь через косую черту.",
            "format_hint": "Например: 3/5",
            "example": "3/5",
            "input_mode": "text",
        }
    if expected and _UNIT_VALUE_RE.fullmatch(expected):
        return {
            "prompt": "Запиши значение вместе с единицей измерения.",
            "format_hint": "Например: 12 см",
            "example": "12 см",
            "input_mode": "text",
        }
    if expected and (_EXPRESSION_MARKER_RE.search(expected) or "выражен" in folded):
        return {
            "prompt": "Запиши выражение или равенство этого перехода.",
            "format_hint": "Например: x = 12 - 5",
            "example": "x = 12 - 5",
            "input_mode": "text",
        }
    if expected and _SIMPLE_NUMBER_RE.fullmatch(expected):
        if expected.endswith("%") or "процент" in folded:
            return {
                "prompt": "Запиши число со знаком процента.",
                "format_hint": "Например: 25%",
                "example": "25%",
                "input_mode": "decimal",
            }
        return {
            "prompt": "Запиши число, которое получилось на этом шаге.",
            "format_hint": "Например: 7",
            "example": "7",
            "input_mode": "decimal",
        }
    if any(word in folded for word in ("выбери", "сравни", "вывод", "объясни")):
        return {
            "prompt": "Запиши короткий вывод своими словами.",
            "format_hint": "Одно короткое предложение",
            "example": "Первая величина больше",
            "input_mode": "text",
        }
    return {
        "prompt": "Запиши результат только текущего шага.",
        "format_hint": "Короткий ответ или выражение",
        "example": "Короткая запись шага",
        "input_mode": "text",
    }


def safe_step_instruction(
    instruction: str,
    *,
    expected_value: object,
    correct_answer: object | None = None,
) -> str:
    """Убирает готовый expected/final answer из user-visible инструкции.

    Исходный полный текст остаётся в БД и в закрытом AI-grounding. Публикация
    fail-closed: если после нескольких срезов cue всё ещё раскрывает ответ,
    возвращается содержательная инструкция по типу действия.
    """
    source = _SPACE_RE.sub(" ", instruction).strip()
    protected = [expected_value]
    if correct_answer is not None:
        protected.append(correct_answer)
    protected = [value for value in protected if str(value).strip()]
    if not source or not protected:
        return source or _fallback_instruction(instruction)

    candidate = source
    for _ in range(4):
        cut = _reveal_cut(candidate, protected)
        if cut is None:
            return candidate
        prefix = candidate[:cut].rstrip(" \t\n:;,—–-")
        if (
            len(prefix) < 8
            or len(prefix.split()) < 2
            or _ACTION_VERB_RE.search(prefix) is None
        ):
            return _fallback_instruction(source)
        candidate = f"{prefix.rstrip('.?')}."

    return _fallback_instruction(source)
