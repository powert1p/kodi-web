"""Скрипт для добавления подсказок единиц измерения в условия задач.

Проблема: ученик пишет "60" (минут), а система ждёт "1" (час),
потому что условие не указывает в каких единицах давать ответ.

Запуск:
  python patch_units.py --dry-run     # только показать что изменится
  python patch_units.py               # сохранить изменения
"""
import json
import re
import sys
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "problems_v10.json"

# ── Подсказки на RU и KZ ──

UNIT_HINT_RU = {
    'ч': '(Ответ в часах)',
    'мин': '(Ответ в минутах)',
    'сек': '(Ответ в секундах)',
    'дн': '(Ответ в днях)',
    'мес': '(Ответ в месяцах)',
    'км': '(Ответ в км)',
    'м': '(Ответ в метрах)',
    'см': '(Ответ в см)',
    'дм': '(Ответ в дм)',
    'мм': '(Ответ в мм)',
    'км/ч': '(Ответ в км/ч)',
    'м/с': '(Ответ в м/с)',
    'м/мин': '(Ответ в м/мин)',
    'кг': '(Ответ в кг)',
    'г': '(Ответ в граммах)',
    'т': '(Ответ в тоннах)',
    'ц': '(Ответ в центнерах)',
    'л': '(Ответ в литрах)',
    'мл': '(Ответ в мл)',
    'м²': '(Ответ в м²)',
    'см²': '(Ответ в см²)',
    'км²': '(Ответ в км²)',
    'га': '(Ответ в га)',
    'м³': '(Ответ в м³)',
}

UNIT_HINT_KZ = {
    'ч': '(Жауап сағатпен)',
    'мин': '(Жауап минутпен)',
    'сек': '(Жауап секундпен)',
    'дн': '(Жауап күнмен)',
    'мес': '(Жауап аймен)',
    'км': '(Жауап км-мен)',
    'м': '(Жауап метрмен)',
    'см': '(Жауап см-мен)',
    'дм': '(Жауап дм-мен)',
    'мм': '(Жауап мм-мен)',
    'км/ч': '(Жауап км/сағ)',
    'м/с': '(Жауап м/с)',
    'м/мин': '(Жауап м/мин)',
    'кг': '(Жауап кг-мен)',
    'г': '(Жауап граммен)',
    'т': '(Жауап тоннамен)',
    'ц': '(Жауап центнермен)',
    'л': '(Жауап литрмен)',
    'мл': '(Жауап мл-мен)',
    'м²': '(Жауап м²-мен)',
    'см²': '(Жауап см²-мен)',
    'км²': '(Жауап км²-мен)',
    'га': '(Жауап га-мен)',
    'м³': '(Жауап м³-мен)',
}


# ── Определение единиц из контекста ──

def _detect_time_unit(text: str) -> str | None:
    """Определить единицу времени из контекста задачи."""
    t = text.lower()
    # Порядок: от мелких к крупным (если есть минуты — ответ в минутах)
    if re.search(r'\b(?:минут|мин)\b', t):
        return 'мин'
    if re.search(r'\b(?:секунд|сек)\b', t):
        return 'сек'
    if re.search(r'\b(?:часов|часа|час|ч)\b', t):
        return 'ч'
    if re.search(r'\b(?:суток|сут|дней|дня|день)\b', t):
        return 'дн'
    if re.search(r'\b(?:месяц|мес)\b', t):
        return 'мес'
    return None


def _detect_distance_unit(text: str) -> str | None:
    t = text.lower()
    if re.search(r'\bкм\b', t):
        return 'км'
    if re.search(r'\bм\b', t):
        return 'м'
    if re.search(r'\bсм\b', t):
        return 'см'
    if re.search(r'\bдм\b', t):
        return 'дм'
    return None


def _detect_speed_unit(text: str) -> str | None:
    t = text.lower()
    if re.search(r'км/ч|км/час', t):
        return 'км/ч'
    if re.search(r'м/с', t):
        return 'м/с'
    if re.search(r'м/мин', t):
        return 'м/мин'
    return None


def _detect_mass_unit(text: str) -> str | None:
    t = text.lower()
    if re.search(r'\bтонн|\bт\b', t):
        return 'т'
    if re.search(r'\bцентнер|\bц\b', t):
        return 'ц'
    if re.search(r'\bкг\b', t):
        return 'кг'
    if re.search(r'\bграмм|\bг\b', t):
        return 'г'
    return None


# ── Проверка: уже есть подсказка? ──

def _already_has_hint(text: str) -> bool:
    """Текст уже содержит указание единиц ответа."""
    t = text.lower()
    # Формат: (Ответ в ...) или (Жауап ...)
    if re.search(r'\((?:ответ|жауап)\s', t):
        return True
    # Формат без скобок: "Дайте ответ в минутах", "ответ запишите в часах"
    if re.search(r'(?:дайте|запишите|выразите|укажите)\s+ответ\s+в\s+\w+', t):
        return True
    if re.search(r'ответ\s+(?:дайте|запишите|укажите|выразите)\s+в\s+\w+', t):
        return True
    # "Дайте ответ в минутах"
    if re.search(r'ответ\s+в\s+(?:минутах|часах|секундах|днях|метрах|км|см|дм|мм|кг|граммах|литрах|м²)', t):
        return True
    return False


# ── Вопрос спрашивает про количество, а не единицы? ──

_QUANTITY_PATTERNS = [
    r'сколько\s+(?:деталей|изделий|домов|колец|ям|штук|банок|животных|колхозн)',
    r'какую\s+часть',
    r'сколько\s+(?:ещё\s+)?(?:нужно\s+)?(?:кранов|рабочих|станков|мастеров|тракторист)',
    r'сколько\s+(?:получит|заработа|стоит|тенге|тг|рублей|денег)',
    r'сколько\s+(?:всего|нужно)\s+\w+\s+(?:для|чтобы)',
]


def _asks_quantity(text: str) -> bool:
    """Вопрос спрашивает про количество предметов, а не единицы измерения."""
    t = text.lower()
    for pat in _QUANTITY_PATTERNS:
        if re.search(pat, t):
            return True
    return False


# ── Вопрос уже содержит единицу в формулировке? ──

_EXPLICIT_UNIT_PATTERNS = [
    r'за сколько часов',
    r'сколько часов',
    r'за сколько минут',
    r'сколько минут',
    r'за сколько секунд',
    r'за сколько дней',
    r'сколько дней',
    r'через сколько часов',
    r'через сколько минут',
    r'переведите.*в\s+\w+',
    r'выразите.*в\s+\w+',
    r'сколько\s+(?:метров|километров|сантиметров|дециметров|миллиметров)',
    r'сколько\s+(?:граммов|килограммов|тонн|центнеров)',
    r'сколько\s+(?:литров|миллилитров)',
]


def _has_explicit_unit_in_question(text: str) -> bool:
    t = text.lower()
    for pat in _EXPLICIT_UNIT_PATTERNS:
        if re.search(pat, t):
            return True
    return False


# ── Определение подсказки для задачи ──

# Паттерны вопросов про время
_TIME_QUESTION_RE = re.compile(
    r'за сколько\b(?!.*(?:деталей|изделий|домов|колец|ям|штук|кранов|рабочих))'
    r'|за какое время'
    r'|через сколько\b',
    re.IGNORECASE
)

# Паттерны вопросов про расстояние
_DISTANCE_QUESTION_RE = re.compile(
    r'какое расстояние|какова?\s+дистанция',
    re.IGNORECASE
)

# Паттерны вопросов про скорость
_SPEED_QUESTION_RE = re.compile(
    r'какова?\s+скорость|найдите скорость|определите скорость|с какой скоростью',
    re.IGNORECASE
)


def determine_hint(problem: dict) -> str | None:
    """Определить какую подсказку добавить. None = не нужна."""
    text = problem.get('text_ru', '')

    # Уже есть подсказка
    if _already_has_hint(text):
        return None

    # Вопрос уже содержит единицу
    if _has_explicit_unit_in_question(text):
        return None

    # Спрашивает про количество — не нужна подсказка
    if _asks_quantity(text):
        return None

    # Вопрос про время
    if _TIME_QUESTION_RE.search(text):
        return _detect_time_unit(text)

    # Вопрос про расстояние
    if _DISTANCE_QUESTION_RE.search(text):
        return _detect_distance_unit(text)

    # Вопрос про скорость
    if _SPEED_QUESTION_RE.search(text):
        return _detect_speed_unit(text)

    return None


# ── Фиксы данных (ответы с неправильными единицами) ──

DATA_FIXES = [
    {
        # Баг со скриншота: "за 12 минут...за 15 минут" → answer=1 (час), должно быть 60 (минут)
        "match": lambda p: (
            p.get("node_id") == "WP05"
            and p["answer"] == "1"
            and "12 минут" in p["text_ru"]
            and "15 минут" in p["text_ru"]
        ),
        "fix_answer": "60",
        "fix_display_answer": "60",
        "fix_acceptable": ["60"],
        "fix_solution_ru": "Скорость совместной работы: 1/12. Скорость первого: 1/15.\nСкорость второго: 1/12 − 1/15 = 5/60 − 4/60 = 1/60.\nВремя второго: 60 минут.",
        "reason": "Ответ был 1 (час), но условие в минутах → правильно 60 минут",
    },
]


def apply_data_fixes(problems: list[dict]) -> list[str]:
    """Применить фиксы данных. Возвращает список описаний."""
    fixes_applied = []
    for p in problems:
        for fix in DATA_FIXES:
            if fix["match"](p):
                old_answer = p["answer"]
                p["answer"] = fix["fix_answer"]
                if "fix_display_answer" in fix:
                    p["display_answer"] = fix["fix_display_answer"]
                if "fix_acceptable" in fix:
                    p["acceptable_answers"] = fix["fix_acceptable"]
                if "fix_solution_ru" in fix:
                    p["solution_ru"] = fix["fix_solution_ru"]
                fixes_applied.append(
                    f"[{p['node_id']}] answer: {old_answer} → {fix['fix_answer']} | {fix['reason']}"
                )
    return fixes_applied


# ── Main ──

def main():
    dry_run = "--dry-run" in sys.argv

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    problems = data["problems"]
    target_cats = (
        {f"WP{i:02d}" for i in range(1, 11)}
        | {f"CV{i:02d}" for i in range(1, 7)}
    )

    # 1) Фиксы данных
    fixes = apply_data_fixes(problems)
    if fixes:
        print(f"\n{'='*60}")
        print(f"ФИКСЫ ДАННЫХ: {len(fixes)}")
        print(f"{'='*60}")
        for f_desc in fixes:
            print(f"  {f_desc}")

    # 2) Добавление подсказок
    changed = []
    skipped_has_hint = 0
    skipped_has_unit = 0
    skipped_quantity = 0
    skipped_no_match = 0

    for p in problems:
        node = p.get("node_id", "")
        if node not in target_cats:
            continue

        text = p.get("text_ru", "")

        if _already_has_hint(text):
            skipped_has_hint += 1
            continue

        if _has_explicit_unit_in_question(text):
            skipped_has_unit += 1
            continue

        if _asks_quantity(text):
            skipped_quantity += 1
            continue

        unit = determine_hint(p)
        if unit is None:
            skipped_no_match += 1
            continue

        hint_ru = UNIT_HINT_RU.get(unit)
        hint_kz = UNIT_HINT_KZ.get(unit)
        if not hint_ru:
            skipped_no_match += 1
            continue

        old_text = p["text_ru"]
        p["text_ru"] = f'{old_text}\n{hint_ru}'
        if p.get("text_kz") and hint_kz:
            p["text_kz"] = f'{p["text_kz"]}\n{hint_kz}'

        changed.append({
            "node_id": node,
            "unit": unit,
            "hint": hint_ru,
            "text_preview": old_text[:100],
            "answer": p["answer"],
        })

    # Отчёт
    print(f"\n{'='*60}")
    print(f"ПОДСКАЗКИ ЕДИНИЦ: {len(changed)} задач обновлено")
    print(f"  Уже есть подсказка: {skipped_has_hint}")
    print(f"  Единица в вопросе: {skipped_has_unit}")
    print(f"  Вопрос про количество: {skipped_quantity}")
    print(f"  Нет совпадения: {skipped_no_match}")
    print(f"{'='*60}\n")

    for c in changed:
        print(f"  [{c['node_id']}] {c['text_preview'][:80]}...")
        print(f"    answer={c['answer']}  →  {c['hint']}")
        print()

    if dry_run:
        print("DRY RUN — файл НЕ сохранён")
        return

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Сохранено в {DATA_FILE}")


if __name__ == "__main__":
    main()
