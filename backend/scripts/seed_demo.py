"""Идемпотентный сид демо-студента для локальной live-верификации.

Создаёт студента с телефоном +70000000000 / PIN 0000, если его нет.
Вставляет 3 неверные диагностические попытки на задачи с decomposition
+ fingerprint, чтобы /api/trainer/wrong-tasks возвращал непустой список.

Запуск:
    cd backend && ../.venv/bin/python scripts/seed_demo.py

Не затрагивает существующие данные (ON CONFLICT DO NOTHING / guard по phone).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем backend/ в sys.path — скрипт запускается из backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import text

from db.base import async_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Параметры демо-студента ───────────────────────────────────────────────────
DEMO_PHONE = "+70000000000"
DEMO_NAME = "Демо"
DEMO_PIN = "0000"

# Число демо-ошибок. Сами задачи подбираются ДИНАМИЧЕСКИ под текущую БД —
# id задач различаются между БД (dev nismathbot ≠ прод kodi), поэтому НЕ хардкодим problem_id.
DEMO_COUNT = 3


def _hash_pin(pin: str) -> str:
    """Хешируем PIN через bcrypt (аналогично routes.py)."""
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


async def seed() -> None:
    async with async_session() as session:
        async with session.begin():
            # ── 1. Создаём демо-студента, если не существует ──────────────────
            existing = await session.execute(
                text("SELECT id FROM students WHERE phone = :phone"),
                {"phone": DEMO_PHONE},
            )
            row = existing.fetchone()

            if row is None:
                pin_hash = _hash_pin(DEMO_PIN)
                # id=999999999 — фиксированный «демо-ID», не пересекается с TG user_id
                await session.execute(
                    text(
                        "INSERT INTO students "
                        "  (id, phone, full_name, pin_hash, registered, lang, "
                        "   created_at, diagnostic_complete) "
                        "VALUES (:id, :phone, :name, :pin_hash, true, 'ru', now(), false) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": 999_999_999,
                        "phone": DEMO_PHONE,
                        "name": DEMO_NAME,
                        "pin_hash": pin_hash,
                    },
                )
                # Перечитываем — мог быть конфликт по id, возьмём реальный
                existing = await session.execute(
                    text("SELECT id FROM students WHERE phone = :phone"),
                    {"phone": DEMO_PHONE},
                )
                row = existing.fetchone()
                log.info("Создан демо-студент phone=%s", DEMO_PHONE)
            else:
                log.info("Демо-студент уже существует phone=%s", DEMO_PHONE)

            student_id: int = row[0]  # type: ignore[index]

            # ── 2. Динамически подбираем задачи под ТЕКУЩУЮ БД (идемпотентно) ──
            # Пропускаем, если у студента уже есть неверные diagnostic-попытки.
            cnt = await session.execute(
                text(
                    "SELECT COUNT(*) FROM attempts "
                    "WHERE student_id = :sid AND source = 'diagnostic' AND is_correct = false"
                ),
                {"sid": student_id},
            )
            existing_count = cnt.scalar() or 0
            if existing_count >= DEMO_COUNT:
                log.info("Попытки уже есть — пропускаем вставку (%d записей)", existing_count)
                return

            # Берём decomposition с реальным problems_db_id + fingerprint (wrong_answer):
            # так build_wrong_tasks вернёт задачу с шагами, а match_fingerprint даст причину.
            picks = await session.execute(
                text(
                    "SELECT dp.problems_db_id AS pid, p.node_id AS nid, pf.wrong_answer AS ans "
                    "FROM decomposition_problems dp "
                    "JOIN problems p ON p.id = dp.problems_db_id "
                    "JOIN problem_fingerprints pf ON pf.decomp_idx = dp.idx "
                    "WHERE dp.problems_db_id IS NOT NULL AND dp.all_steps_verified = true "
                    "ORDER BY dp.idx LIMIT :lim"
                ),
                {"lim": DEMO_COUNT},
            )
            rows = picks.fetchall()
            if not rows:
                log.warning("Нет слинкованных decomposition+fingerprint задач — нечего сеять")
                return

            for r in rows:
                await session.execute(
                    text(
                        "INSERT INTO attempts "
                        "  (student_id, problem_id, node_id, answer_given, "
                        "   is_correct, source, created_at) "
                        "VALUES (:sid, :pid, :nid, :ans, false, 'diagnostic', now())"
                    ),
                    {"sid": student_id, "pid": r.pid, "nid": r.nid, "ans": r.ans},
                )

            log.info("Вставлено %d неверных попыток для student_id=%d", len(rows), student_id)


if __name__ == "__main__":
    asyncio.run(seed())
