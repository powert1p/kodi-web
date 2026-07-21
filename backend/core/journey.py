"""Product contract for the adaptive NIS photo-first learning journey."""

from __future__ import annotations

from typing import Any


EXAM_MAP: dict[str, Any] = {
    "title": "Первый день конкурсного отбора NIS",
    "cycle": "2026–2027",
    "verified_on": "16 июля 2026",
    "source_url": "https://www.nis.edu.kz/ru/page/konkurs-zoninde-xabarlama",
    "source_note": (
        "Формат сверен с условиями отбора на 2026–2027 учебный год. "
        "Условия следующего цикла NIS пока не опубликованы."
    ),
    "disclaimer": (
        "AiPlus — независимая подготовка по математике. Это не продукт и не "
        "официальный тренажёр NIS."
    ),
    "scope_note": (
        "В приложении мы готовим к двум математическим блокам. "
        "Естествознание и языковые тесты пока не входят в маршрут."
    ),
    "day_one": [
        {"name": "Математика", "questions": 40, "minutes": 60, "covered": True},
        {
            "name": "Количественные характеристики",
            "questions": 60,
            "minutes": 30,
            "covered": True,
        },
        {
            "name": "Естествознание",
            "questions": 20,
            "minutes": 30,
            "covered": False,
        },
    ],
}


DIAGNOSTIC_ANCHORS = [127, 321, 876, 1144, 1409]
DIAGNOSTIC_EASIER = {
    127: 121,
    321: 320,
    876: 448,
    1144: 544,
    1409: 804,
}
DIAGNOSTIC_NODE_BY_ANCHOR = {
    127: "FR05",
    321: "PC05",
    876: "EQ04",
    1144: "GE04",
    1409: "DA02",
}
DIAGNOSTIC_SKILLS = {
    127: {"id": "FR05", "title": "Дроби"},
    321: {"id": "PC05", "title": "Проценты"},
    876: {"id": "EQ04", "title": "Текстовые уравнения"},
    1144: {"id": "GE04", "title": "Геометрические отношения"},
    1409: {"id": "DA02", "title": "Графики и данные"},
}
DIAGNOSTIC_LEVEL_LABELS = {
    "foundation": "Нужна база",
    "developing": "В процессе",
    "secure": "Опора есть",
    "unmeasured": "Нет данных",
}
DIAGNOSTIC_MASTERY_PRIORS = {
    "foundation": 0.2,
    "developing": 0.35,
    "secure": 0.55,
    "unmeasured": 0.1,
}


TOPIC_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "PC06": {
        "id": "PC06",
        "title": "Смеси и концентрации",
        "strand": "Отношения и пропорции",
        "goal": "Научиться сохранять количество вещества при изменении раствора.",
        "target_content_idx": 1765,
        "transfer_content_idx": 331,
        "reinforcement_content_indices": [332, 333, 328, 329, 330, 895, 922, 944],
        "diagnostic_anchor": 321,
        "weak_reason": (
            "Диагностика показала пробел в процентах — он мешает уверенно решать смеси."
        ),
        "foundation_reason": (
            "Начнём с основы: в процентах пока теряется связь между частью и целым."
        ),
        "strong_reason": (
            "Проценты уже знакомы; закрепим их в сложных задачах на концентрацию."
        ),
    },
    "EQ04": {
        "id": "EQ04",
        "title": "Текстовые задачи через уравнение",
        "strand": "Алгебраическая модель",
        "goal": "Переводить условие задачи в одно уравнение и проверять смысл ответа.",
        "target_content_idx": 453,
        "transfer_content_idx": 890,
        "reinforcement_content_indices": [905, 919, 951, 995, 999, 1036],
        "diagnostic_anchor": 876,
        "weak_reason": (
            "В диагностике было трудно собрать условие в уравнение — начнём с этого навыка."
        ),
        "foundation_reason": (
            "Сначала восстановим основу: как переводить величины из условия в уравнение."
        ),
        "strong_reason": (
            "Базовая модель получилась; проверим перенос на более насыщенное условие."
        ),
    },
    "FR05": {
        "id": "FR05",
        "title": "Сравнение и смысл дробей",
        "strand": "Числа и дроби",
        "goal": "Сравнивать дроби через общий смысл, а не угадывать по числам.",
        "target_content_idx": 122,
        "transfer_content_idx": 1659,
        "reinforcement_content_indices": [
            1641,
            1642,
            1431,
            1657,
            1656,
        ],
        "diagnostic_anchor": 127,
        "weak_reason": (
            "В диагностике сравнение дробей потребовало опоры — соберём надёжный способ."
        ),
        "foundation_reason": (
            "Начнём со смысла дроби и расстояния до знакомых опор: 0, 1/2 и 1."
        ),
        "strong_reason": (
            "Основа дробей уже есть; закрепим её на сравнении без длинных вычислений."
        ),
    },
    "GE04": {
        "id": "GE04",
        "title": "Углы и отношения",
        "strand": "Геометрические отношения",
        "goal": "Переводить отношение частей угла в точную градусную меру.",
        "target_content_idx": 2385,
        "transfer_content_idx": 2472,
        "reinforcement_content_indices": [
            1106,
            1293,
            1286,
            1307,
            2370,
            2304,
            1200,
            1219,
        ],
        "diagnostic_anchor": 1144,
        "weak_reason": (
            "Диагностика показала, что отношение углов пока трудно связать с целым."
        ),
        "foundation_reason": (
            "Восстановим основу: что является целым углом и сколько градусов приходится на одну долю."
        ),
        "strong_reason": (
            "Угловые отношения уже знакомы; проверим их на задаче с несколькими частями."
        ),
    },
    "DA02": {
        "id": "DA02",
        "title": "Графики движения и данных",
        "strand": "Данные и зависимости",
        "goal": "Считывать изменения с графика и связывать их с расчётом величины.",
        "target_content_idx": 2043,
        "transfer_content_idx": 2046,
        "reinforcement_content_indices": [2044, 806, 2045, 802],
        "diagnostic_anchor": 1409,
        "weak_reason": (
            "В диагностике было трудно собрать несколько участков графика в один расчёт."
        ),
        "foundation_reason": (
            "Начнём с чтения осей, участков движения и величин, которые нельзя смешивать."
        ),
        "strong_reason": (
            "Графики читаются уверенно; закрепим перенос на составное движение."
        ),
    },
}


def initial_diagnostic(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Создаёт диагностику, используя самооценку только для порядка вопросов.

    Сильные/слабые темы не становятся evidence и не меняют BKT: все пять
    проверенных anchor-задач всё равно остаются в очереди.
    """

    profile = profile or {}
    anchor_by_skill = {
        skill["id"]: anchor for anchor, skill in DIAGNOSTIC_SKILLS.items()
    }
    weak = [
        anchor_by_skill[skill_id]
        for skill_id in profile.get("weak_topics") or []
        if skill_id in anchor_by_skill
    ]
    strong = [
        anchor_by_skill[skill_id]
        for skill_id in profile.get("strong_topics") or []
        if skill_id in anchor_by_skill and anchor_by_skill[skill_id] not in weak
    ]
    neutral = [
        anchor
        for anchor in DIAGNOSTIC_ANCHORS
        if anchor not in weak and anchor not in strong
    ]
    return {
        "queue": [*weak, *neutral, *strong],
        "position": 0,
        "answers": [],
        "completed": False,
    }


def anchor_was_correct(diagnostic: dict[str, Any], anchor: int) -> bool | None:
    for answer in diagnostic.get("answers", []):
        if int(answer.get("question_id", -1)) == anchor:
            return bool(answer.get("correct"))
    return None


def diagnostic_level(diagnostic: dict[str, Any], anchor: int) -> str:
    """Возвращает уровень с учётом опорного и более простого вопроса."""

    anchor_correct = anchor_was_correct(diagnostic, anchor)
    if anchor_correct is True:
        return "secure"
    if anchor_correct is None:
        return "unmeasured"
    easier = DIAGNOSTIC_EASIER.get(anchor)
    if easier is not None and anchor_was_correct(diagnostic, easier) is True:
        return "developing"
    return "foundation"


def diagnostic_mastery_prior(diagnostic: dict[str, Any], anchor: int) -> float:
    """Переводит адаптивную диагностическую ступень в консервативный BKT prior."""

    return DIAGNOSTIC_MASTERY_PRIORS[diagnostic_level(diagnostic, anchor)]


def build_route(diagnostic: dict[str, Any]) -> dict[str, Any]:
    """Строит короткий объяснимый маршрут из реальных задач банка."""
    priority = {"foundation": 0, "developing": 1, "secure": 2, "unmeasured": 3}
    ordered_ids = sorted(
        TOPIC_BLUEPRINTS,
        key=lambda topic_id: (
            priority[
                diagnostic_level(
                    diagnostic,
                    int(TOPIC_BLUEPRINTS[topic_id]["diagnostic_anchor"]),
                )
            ],
            list(TOPIC_BLUEPRINTS).index(topic_id),
        ),
    )

    topics: list[dict[str, Any]] = []
    for topic_id in ordered_ids:
        blueprint = TOPIC_BLUEPRINTS[topic_id]
        level = diagnostic_level(
            diagnostic,
            int(blueprint["diagnostic_anchor"]),
        )
        if level == "foundation":
            reason = blueprint["foundation_reason"]
        elif level == "developing":
            reason = blueprint["weak_reason"]
        else:
            reason = blueprint["strong_reason"]
        topics.append(
            {
                "id": topic_id,
                "title": blueprint["title"],
                "strand": blueprint["strand"],
                "goal": blueprint["goal"],
                "reason": reason,
                "diagnostic_level": level,
                "status": "next" if not topics else "planned",
            }
        )

    routed_anchors = {
        int(blueprint["diagnostic_anchor"]): topic_id
        for topic_id, blueprint in TOPIC_BLUEPRINTS.items()
    }
    skill_profile = []
    for anchor in DIAGNOSTIC_ANCHORS:
        skill = DIAGNOSTIC_SKILLS[anchor]
        level = diagnostic_level(diagnostic, anchor)
        skill_profile.append(
            {
                **skill,
                "level": level,
                "label": DIAGNOSTIC_LEVEL_LABELS[level],
                "route_topic_id": routed_anchors.get(anchor),
            }
        )
    return {
        "topics": topics,
        "index": 0,
        "completed": [],
        "skill_profile": skill_profile,
    }


def topic_blueprint(topic_id: str) -> dict[str, Any]:
    try:
        return TOPIC_BLUEPRINTS[topic_id]
    except KeyError as exc:  # pragma: no cover - durable-state invariant
        raise ValueError(f"Неизвестная тема маршрута: {topic_id}") from exc


def diagnostic_score(diagnostic: dict[str, Any]) -> tuple[int, int]:
    anchor_answers = [
        answer
        for answer in diagnostic.get("answers", [])
        if int(answer.get("question_id", -1)) in DIAGNOSTIC_ANCHORS
    ]
    return sum(bool(answer.get("correct")) for answer in anchor_answers), len(
        anchor_answers
    )
