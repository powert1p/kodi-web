"""
seed_decomposition.py — стратегия привязки full_decomposition_v1.json к таблице problems.

=== Контекст ===
Файл docs/specs/full_decomposition_v1.json содержит 2525 записей с полями:
    idx               : int   — порядковый номер (0..2524), НЕ соответствует problems.id
    node_id           : str   — идентификатор узла графа (напр. "AR01"), совпадает с DB
    answer            : str   — ответ задачи
    primary_micro_skill: str  — главный микро-навык
    steps             : list  — верифицированные шаги решения
    fingerprints      : list  — сигнатуры ошибок
    all_steps_verified: bool
    needs_review      : bool
    review_reason     : str

Полей text_ru / text_kz в декомпозиции НЕТ — они только в DB.

=== Результаты зондирования (2025-06-25, полный скан 2525 записей) ===

База данных: 1794 задачи (id 16675..18468), 118 узлов.
Декомпозиция: 2525 задач, 118 узлов (те же узлы, но другой банк задач).

Стратегия A: idx → problems.id (прямое или +1)
    → 0/2525 совпадений. idx ∈ [0..2524], DB id ∈ [16675..18468] — диапазоны не пересекаются.

Стратегия B: (node_id, answer) → уникальный problems.id
    → UNIQUE (ровно 1 совпадение): 1059/2525 = 41.9%
    → AMBIG  (>1 совпадений):      458/2525  = 18.1%
    → NONE   (0 совпадений):       1008/2525 = 39.9%

Стратегия C: (node_id, text_ru[:40]) — невозможна: text_ru в декомпозиции отсутствует.

=== Вывод ===
Полноценный JOIN декомпозиции с таблицей problems НЕВОЗМОЖЕН: датасеты генерировались
независимо. DB-задачи были сидированы из problems_v10.json (поле text_ru, своя нумерация).
Декомпозиция — отдельный банк с той же разбивкой по node_id, но разными условиями задач.

=== Выбранная стратегия для сидирования (Task 3) ===
Декомпозиция хранится в ОТДЕЛЬНОЙ таблице (decomposition_problems) с собственным PK = idx.
Привязка к DB: для 41.9% записей (unique_match) поле problems_db_id заполняется через
    (node_id, answer) lookup — ровно 1 совпадение; для остальных NULL.
Поле node_id является FK на nodes.id и служит «мягкой» связью для всех 100% записей.
Логика join при запросе к пользователю: сначала по problems_db_id (если не NULL),
    иначе по node_id (любая задача узла из DB).

JOIN-ключи в application-коде:
    SELECT p.id FROM problems p
    WHERE p.node_id = :node_id AND p.answer = :answer
    -- применять только если COUNT(*) = 1 для данного (node_id, answer)
"""

# TODO Task 3: реализовать сидирование таблицы decomposition_problems
