# CC Graph Topic Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить плоские 15 тегов графа в настоящий уровень иерархии Раздел→Тема→навык (43 темы Common Core + 61 ребро), не трогая 118 узлов / 2525 задач / mastery / движок.

**Architecture:** Additive слой над существующим графом. Новые таблицы `topics` + `topic_edges`, новая колонка `nodes.topic_id` (мост 118→43). API `/graph/me` дополняется массивами `topics`/`strands` и `topic_id` на узлах (старые поля целы). Фронт `graph_page.dart` рендерит вложенный аккордеон вместо плоской группировки по тегу. Bootstrap идемпотентен (работает на свежей и на задеплоенной БД).

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 async + asyncpg (backend); Flutter Web + BLoC (frontend); pytest + pytest-asyncio (тесты).

## Global Constraints

- Backend SQL: ТОЛЬКО параметризованный (ORM `select()` / `text()` с bind). Комментарии на русском.
- Async везде; `async def` хендлеры; `await session.execute(...)`.
- НЕ трогать 118 узлов, 2525 задач, mastery, attempts, BKT, движок (diagnostic/practice/exam/fringe/zones).
- НЕТ DROP/DELETE/TRUNCATE. Все ALTER идемпотентны (`IF NOT EXISTS`), upsert через `ON CONFLICT DO UPDATE`.
- Темы — только вид графа, не гейтят путь.
- Frontend: новый текст — в ОБА `.arb` (app_ru.arb + app_kk.arb), без хардкода строк. TypeScript/Dart strict, без `any`/`dynamic` где можно. Компонент-файлы небольшие.
- Источник данных: `docs/specs/cc_topic_skill_tree.json` (43 topics, 61 topic_edges, 337 skills с Russian `label`+`domain`+`topic`, `cc_domains_ru`(9), `nis_groups_ru`(4)).
- Грейн темы = CC-кластер (43). Strand = `domain` (9 CC: OA/NBT/NF/MD/G/EE/NS/RP/SP) + 1 НИШ (domain="NIS", 4 темы) = 10 разделов.
- CC-коды (`6.RP.A`) НЕ показывать в UI — только ru/kz-название (код хранится в данных).

---

### Task 1: Сгенерировать `backend/data/cc_topics_v01.json`

Данные для слоя тем: разделы (ru/kz), 43 темы (ru/kz-названия, strand, класс, порядок), 61 ребро, мост узел→тема для всех 118 узлов.

**Files:**
- Create: `backend/data/cc_topics_v01.json`
- Create: `scripts/build_cc_topics.py` (детерминированный трансформер: strands+topics+edges из источника; node→topic map подставляется)
- Test: `backend/tests/test_cc_topics_data.py`

**Interfaces:**
- Produces: файл `cc_topics_v01.json` со схемой:
  ```json
  {
    "meta": {"topics": 43, "edges": 61, "nodes_mapped": 118},
    "strands": [{"code": "RP", "order": 1, "name_ru": "...", "name_kz": "..."}],
    "topics": [{"id": "6.RP.A", "strand": "RP", "grade": 6, "order": 1, "name_ru": "...", "name_kz": "..."}],
    "topic_edges": [["4.MD.A", "6.RP.A"]],
    "node_topic": {"AR01": "7.NS.A"}
  }
  ```
  - `strands`: 10 (9 CC domains в порядке OA,NBT,NF,MD,G,EE,NS,RP,SP + NIS=10). `name_ru` из `cc_domains_ru`; NIS → "НИШ-математика".
  - `topics`: 43. `strand` = topic.domain. `grade` из источника (NIS → null). `order` = (grade, code). NIS-темы `name_ru` из `nis_groups_ru`. CC-темы `name_ru`/`name_kz` — короткие осмысленные (сгенерить из label_en + список skills).
  - `topic_edges`: 61 пара [from, to] из источника `topic_edges`.
  - `node_topic`: 118 записей, каждый node.id → topic_id. **Сгенерировать** семантическим матчем имени узла (`name_ru`) к Russian `label` микро-навыков (`skills[].label`), взять `skills[].topic`; `node.tag` использовать как хинт домена. Каждый узел → ровно одна тема.

- [ ] **Step 1: Написать падающий тест-инвариант**

```python
# backend/tests/test_cc_topics_data.py
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "cc_topics_v01.json"
GRAPH = Path(__file__).resolve().parent.parent / "data" / "nis_knowledge_graph_v01.json"


def _load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_counts():
    d = _load()
    assert len(d["topics"]) == 43
    assert len(d["topic_edges"]) == 61
    assert len(d["strands"]) == 10


def test_every_node_mapped_to_existing_topic():
    d = _load()
    topic_ids = {t["id"] for t in d["topics"]}
    graph_nodes = {n["id"] for n in json.loads(GRAPH.read_text(encoding="utf-8"))["nodes"]}
    assert set(d["node_topic"].keys()) == graph_nodes  # 118/118, 0 сирот
    for nid, tid in d["node_topic"].items():
        assert tid in topic_ids, f"{nid} → несуществующая тема {tid}"


def test_topics_have_strand_and_labels():
    d = _load()
    strand_codes = {s["code"] for s in d["strands"]}
    for t in d["topics"]:
        assert t["strand"] in strand_codes
        assert t["name_ru"] and t["name_kz"]


def test_edges_reference_existing_topics():
    d = _load()
    topic_ids = {t["id"] for t in d["topics"]}
    for a, b in d["topic_edges"]:
        assert a in topic_ids and b in topic_ids
```

- [ ] **Step 2: Прогнать — убедиться, что падает**

Run: `.venv/bin/pytest backend/tests/test_cc_topics_data.py -q`
Expected: FAIL (файл `cc_topics_v01.json` ещё не существует → FileNotFoundError).

- [ ] **Step 3: Написать `scripts/build_cc_topics.py` и сгенерировать данные**

Скрипт детерминированно собирает strands/topics/topic_edges из `docs/specs/cc_topic_skill_tree.json`; `node_topic` берёт из словаря, переданного отдельно (результат семантического маппинга — см. ниже). Логика трансформера:
- strands: из `cc_domains_ru` (порядок OA,NBT,NF,MD,G,EE,NS,RP,SP) + NIS; `name_ru` = значение, NIS = "НИШ-математика".
- topics: по каждому из `topics` источника → {id=topic_id, strand=domain, grade, order=(grade или 99, id), name_ru/name_kz}. NIS name_ru = `nis_groups_ru[code]`. CC name_ru/kz — короткие осмысленные названия (сгенерить, не label_en).
- topic_edges: копия `topic_edges`.
- node_topic: вход — отдельный JSON `scripts/node_topic_map.json` ({node_id: topic_id}); скрипт валидирует, что все 118 узлов покрыты и темы существуют, иначе exit 1.

Маппинг узел→тема (`scripts/node_topic_map.json`) сгенерировать семантически: для каждого из 118 узлов (`name_ru`, `tag`) подобрать наиболее близкий микро-навык по Russian `label` среди `skills`, взять его `topic`. `tag` сужает домен. Перепроверить выборку 12–15 спорных вручную.

- [ ] **Step 4: Прогнать — убедиться, что проходит**

Run: `.venv/bin/pytest backend/tests/test_cc_topics_data.py -q`
Expected: PASS (4 теста).

- [ ] **Step 5: Коммит**

```bash
git add backend/data/cc_topics_v01.json scripts/build_cc_topics.py scripts/node_topic_map.json backend/tests/test_cc_topics_data.py
git commit -m "feat: данные слоя тем CC (43 темы, 61 ребро, мост 118→тема)"
```

---

### Task 2: Backend — модели, bootstrap, seed тем

**Files:**
- Modify: `backend/db/models.py` (добавить `Topic`, `TopicEdge`; `Node.topic_id`)
- Modify: `backend/db/seed.py` (добавить `seed_topics`)
- Modify: `backend/run.py:25-60` (ALTER topic_id; вызвать seed_topics всегда)
- Test: `backend/tests/test_seed_topics.py` (integration против реального Postgres; conftest с тестовой БД)

**Interfaces:**
- Consumes: `backend/data/cc_topics_v01.json` (Task 1).
- Produces:
  - `Topic(id: str PK, strand: str, grade: int|None, order_idx: int, name_ru: str, name_kz: str)`
  - `TopicEdge(from_topic: str PK, to_topic: str PK)`
  - `Node.topic_id: str | None`
  - `async def seed_topics(session) -> int` — идемпотентный upsert тем/рёбер + UPDATE node.topic_id; возвращает число тем.

- [ ] **Step 1: Добавить модели в `backend/db/models.py`**

```python
class Topic(Base):
    """Тема графа (CC-кластер или НИШ-группа) — слой над узлами."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # "6.RP.A" / "NIS.COMB"
    strand: Mapped[str] = mapped_column(String(10), nullable=False)  # домен: RP/EE/.../NIS
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    name_ru: Mapped[str] = mapped_column(Text, nullable=False)
    name_kz: Mapped[str] = mapped_column(Text, nullable=False)


class TopicEdge(Base):
    """Ребро-пререквизит между темами (CC coherence map)."""

    __tablename__ = "topic_edges"

    from_topic: Mapped[str] = mapped_column(String(20), ForeignKey("topics.id"), primary_key=True)
    to_topic: Mapped[str] = mapped_column(String(20), ForeignKey("topics.id"), primary_key=True)
```

И в класс `Node` добавить колонку (после `tag`):

```python
    topic_id: Mapped[str | None] = mapped_column(String(20))  # FK на topics.id; на existing-БД без констрейнта
```

- [ ] **Step 2: Написать `seed_topics` в `backend/db/seed.py`**

```python
async def seed_topics(session) -> int:
    """Идемпотентно загрузить темы/рёбра и привязать узлы к темам.

    Безопасно на уже засеянной БД: upsert тем, рёбра по ON CONFLICT,
    node.topic_id обновляется UPDATE из карты. Деструктива нет.
    """
    topics_path = _DATA_DIR / "cc_topics_v01.json"
    if not topics_path.exists():
        logger.warning("cc_topics file not found: %s", topics_path)
        return 0

    d = json.loads(topics_path.read_text(encoding="utf-8"))

    for t in d["topics"]:
        await session.execute(
            text("""
                INSERT INTO topics (id, strand, grade, order_idx, name_ru, name_kz)
                VALUES (:id, :strand, :grade, :order_idx, :name_ru, :name_kz)
                ON CONFLICT (id) DO UPDATE SET
                    strand = EXCLUDED.strand, grade = EXCLUDED.grade,
                    order_idx = EXCLUDED.order_idx,
                    name_ru = EXCLUDED.name_ru, name_kz = EXCLUDED.name_kz
            """),
            {"id": t["id"], "strand": t["strand"], "grade": t.get("grade"),
             "order_idx": t.get("order", 0), "name_ru": t["name_ru"], "name_kz": t["name_kz"]},
        )

    for a, b in d["topic_edges"]:
        await session.execute(
            text("""
                INSERT INTO topic_edges (from_topic, to_topic) VALUES (:a, :b)
                ON CONFLICT (from_topic, to_topic) DO NOTHING
            """),
            {"a": a, "b": b},
        )

    for node_id, topic_id in d["node_topic"].items():
        await session.execute(
            text("UPDATE nodes SET topic_id = :tid WHERE id = :nid"),
            {"tid": topic_id, "nid": node_id},
        )

    await session.commit()
    logger.info("Seeded %d topics, %d topic edges.", len(d["topics"]), len(d["topic_edges"]))
    return len(d["topics"])
```

- [ ] **Step 3: Подключить bootstrap в `backend/run.py`**

В список ALTER (после строки 42) добавить:
```python
            "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS topic_id VARCHAR(20)",
```
В импорт seed: `from db.seed import seed_graph, seed_problems, seed_topics`.
После блока seed (после строки 59, ВНЕ `if count == 0` — выполнять всегда) добавить:
```python
        async with async_session() as session:
            await seed_topics(session)
```

- [ ] **Step 4: Написать integration-тест идемпотентности**

```python
# backend/tests/test_seed_topics.py
import pytest
from sqlalchemy import text
from db.seed import seed_graph, seed_topics

pytestmark = pytest.mark.asyncio


async def test_seed_topics_idempotent(db_session):
    await seed_graph(db_session)
    n1 = await seed_topics(db_session)
    n2 = await seed_topics(db_session)  # повторный прогон не падает
    assert n1 == n2 == 43

    topics = (await db_session.execute(text("SELECT count(*) FROM topics"))).scalar()
    edges = (await db_session.execute(text("SELECT count(*) FROM topic_edges"))).scalar()
    orphans = (await db_session.execute(
        text("SELECT count(*) FROM nodes WHERE topic_id IS NULL"))).scalar()
    assert topics == 43 and edges == 61 and orphans == 0
```

Если `backend/tests/conftest.py` с фикстурой `db_session` (реальный Postgres) нет — создать его в рамках этой задачи (engine из тестового `DATABASE_URL`, create_all, rollback/teardown).

- [ ] **Step 5: Прогнать тесты**

Run: `.venv/bin/pytest backend/tests/test_seed_topics.py -q`
Expected: PASS.

- [ ] **Step 6: Коммит**

```bash
git add backend/db/models.py backend/db/seed.py backend/run.py backend/tests/
git commit -m "feat: схема и идемпотентный сид слоя тем (topics, topic_edges, node.topic_id)"
```

---

### Task 3: API — отдавать темы/разделы в `/graph/me`

**Files:**
- Modify: `backend/core/web_graph.py` (функция `generate_graph_data`, строки 27-208)
- Test: `backend/tests/test_graph_api_topics.py`

**Interfaces:**
- Consumes: таблицы `topics`, `topic_edges`, `nodes.topic_id` (Task 2).
- Produces: dict из `generate_graph_data` дополнительно содержит:
  - на каждом элементе `nodes[]` — поле `"topic_id": str | None`
  - `data["topics"]`: `[{"id", "strand", "grade", "name_ru", "name_kz", "order", "prereq": [topic_id,...], "node_ids": [...]}]` — только темы с ≥1 узлом
  - `data["strands"]`: `[{"code", "name_ru", "name_kz", "order"}]` — только разделы с ≥1 темой, по `order`

- [ ] **Step 1: Написать тест контракта**

```python
# backend/tests/test_graph_api_topics.py
import pytest
from db.seed import seed_graph, seed_topics
from core.web_graph import generate_graph_data

pytestmark = pytest.mark.asyncio


async def test_graph_data_has_topics_and_strands(db_session, seeded_student):
    await seed_graph(db_session)
    await seed_topics(db_session)
    data = await generate_graph_data(db_session, seeded_student, "ru")

    assert "topics" in data and "strands" in data
    assert all("topic_id" in n for n in data["nodes"])  # старые поля целы + новое
    assert all(t["node_ids"] for t in data["topics"])    # только непустые темы
    topic_ids = {t["id"] for t in data["topics"]}
    for t in data["topics"]:
        for p in t["prereq"]:
            assert isinstance(p, str)
    strand_codes = {s["code"] for s in data["strands"]}
    assert all(t["strand"] in strand_codes for t in data["topics"])
```

- [ ] **Step 2: Прогнать — убедиться, что падает**

Run: `.venv/bin/pytest backend/tests/test_graph_api_topics.py -q`
Expected: FAIL (нет ключа "topics").

- [ ] **Step 3: Расширить `generate_graph_data`**

В `backend/core/web_graph.py`: загрузить темы/рёбра, добавить `topic_id` в `node_data`, собрать `topics`/`strands`. После загрузки `all_nodes` (строка ~39) добавить:
```python
    from db.models import Topic, TopicEdge
    topics_rows = list((await session.execute(select(Topic))).scalars().all())
    topic_edges_rows = (await session.execute(select(TopicEdge.from_topic, TopicEdge.to_topic))).all()
```
В `node_data` (строка ~129) добавить `"topic_id": node.topic_id`.
После сборки `nodes_json` (строка ~149) добавить сборку `topics_json`/`strands_json`:
```python
    # ── Темы (только непустые) + разделы ──
    prereq_by_topic: dict[str, list[str]] = {}
    for ft, tt in topic_edges_rows:
        prereq_by_topic.setdefault(tt, []).append(ft)
    nodes_by_topic: dict[str, list[str]] = {}
    for node in all_nodes:
        if node.topic_id:
            nodes_by_topic.setdefault(node.topic_id, []).append(node.id)

    STRAND_NAMES = {  # ru/kz названия разделов (из cc_domains_ru + НИШ)
        # заполнить 10 разделов — берётся из cc_topics_v01.json strands при сиде темы
    }
    topics_json = []
    for t in topics_rows:
        nids = nodes_by_topic.get(t.id, [])
        if not nids:
            continue
        topics_json.append({
            "id": t.id, "strand": t.strand, "grade": t.grade,
            "name_ru": t.name_ru, "name_kz": t.name_kz, "order": t.order_idx,
            "prereq": prereq_by_topic.get(t.id, []),
            "node_ids": nids,
        })
    used_strands = {t["strand"] for t in topics_json}
    # порядок разделов — по минимальному order_idx тем
    strand_order = {}
    for t in topics_rows:
        if t.strand in used_strands:
            strand_order[t.strand] = min(strand_order.get(t.strand, 10**9), t.order_idx)
    strands_json = [
        {"code": s, "order": o} for s, o in sorted(strand_order.items(), key=lambda kv: kv[1])
    ]
```
Названия разделов (`name_ru`/`name_kz`) хранятся в `cc_topics_v01.json.strands` — добавить таблицу `strands` (или отдать имена с фронта по коду). **Решение:** добавить поля имён раздела прямо в `strands_json` из загруженного файла данных (прочитать `cc_topics_v01.json` один раз в `web_graph`), чтобы фронт не хардкодил. Добавить `data["topics"] = topics_json` и `data["strands"] = strands_json`.

- [ ] **Step 4: Прогнать тест**

Run: `.venv/bin/pytest backend/tests/test_graph_api_topics.py -q`
Expected: PASS.

- [ ] **Step 5: Коммит**

```bash
git add backend/core/web_graph.py backend/tests/test_graph_api_topics.py
git commit -m "feat: API /graph/me отдаёт темы и разделы (topics/strands/topic_id)"
```

---

### Task 4: Frontend — модели и парсинг тем

**Files:**
- Modify: `frontend/packages/kodi_core/lib/models/graph_node.dart` (поле `topicId`)
- Create: `frontend/packages/kodi_core/lib/models/graph_topic.dart` (`GraphTopic`, `GraphStrand`)
- Modify: `frontend/packages/kodi_core/lib/kodi_core.dart` (экспорт новых моделей)
- Modify: `frontend/packages/kodi_core/lib/api/nis_api.dart` (парсить topics/strands)
- Modify: `frontend/apps/kodi_web/lib/features/dashboard/bloc/dashboard_bloc.dart` + `dashboard_state.dart` (нести `topics`/`strands` в `DashboardLoaded`)
- Test: `frontend/packages/kodi_core/test/graph_topic_test.dart`

**Interfaces:**
- Consumes: JSON-контракт из Task 3 (`topics[]`, `strands[]`, `topic_id` на узле).
- Produces:
  - `GraphNode.topicId: String?`
  - `GraphTopic { String id, strand, nameRu, nameKz; int? grade; int order; List<String> prereq, nodeIds; String name(String lang); }`
  - `GraphStrand { String code, nameRu, nameKz; int order; String name(String lang); }`
  - `DashboardLoaded` получает `List<GraphTopic> topics`, `List<GraphStrand> strands`.

- [ ] **Step 1: Написать падающий тест fromJson**

```dart
// frontend/packages/kodi_core/test/graph_topic_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:kodi_core/kodi_core.dart';

void main() {
  test('GraphTopic.fromJson parses prereq and nodeIds', () {
    final t = GraphTopic.fromJson({
      'id': '6.RP.A', 'strand': 'RP', 'grade': 6, 'order': 10,
      'name_ru': 'Отношения', 'name_kz': 'Қатынастар',
      'prereq': ['4.MD.A'], 'node_ids': ['PR01', 'PC01'],
    });
    expect(t.id, '6.RP.A');
    expect(t.prereq, ['4.MD.A']);
    expect(t.nodeIds.length, 2);
    expect(t.name('kz'), 'Қатынастар');
  });

  test('GraphStrand.name picks lang', () {
    final s = GraphStrand.fromJson(
        {'code': 'RP', 'name_ru': 'Отношения', 'name_kz': 'Қатынастар', 'order': 1});
    expect(s.name('ru'), 'Отношения');
  });
}
```

- [ ] **Step 2: Прогнать — убедиться, что падает**

Run: `cd frontend/packages/kodi_core && flutter test test/graph_topic_test.dart`
Expected: FAIL (нет `GraphTopic`).

- [ ] **Step 3: Реализовать модели + парсинг + bloc**

Создать `graph_topic.dart` с null-safe `fromJson` (как другие модели в `models/`). Добавить `topicId` в `GraphNode.fromJson` (`json['topic_id'] as String?`). Экспортировать из `kodi_core.dart`. В `nis_api.dart` распарсить `topics`/`strands` из ответа `/graph/me` и вернуть (расширить тип результата или ввести `GraphData {nodes, topics, strands}`). Протянуть в `DashboardLoaded` (+ обновить эмиссии в bloc; default `[]` если ключей нет — обратная совместимость).

- [ ] **Step 4: Прогнать тесты + analyze**

Run: `cd frontend/packages/kodi_core && flutter test test/graph_topic_test.dart && flutter analyze`
Expected: PASS, 0 errors.

- [ ] **Step 5: Коммит**

```bash
git add frontend/packages/kodi_core frontend/apps/kodi_web/lib/features/dashboard/bloc
git commit -m "feat: фронт-модели тем графа (GraphTopic/GraphStrand) + парсинг /graph/me"
```

---

### Task 5: Frontend — иерархия Раздел→Тема→навык на графе

**Files:**
- Modify: `frontend/apps/kodi_web/lib/features/dashboard/pages/graph_page.dart` (вместо `byTag` — вложенный аккордеон по strands→topics→nodes)
- Modify: `frontend/apps/kodi_web/lib/l10n/app_ru.arb` + `app_kk.arb` (новые строки, если нужны: напр. подпись «Темы-предшественники»)
- Read first: `DESIGN_SYSTEM.md`, `lib/app/colors.dart`
- Verify: `flutter analyze`, `flutter build web --release`, Playwright

**Interfaces:**
- Consumes: `DashboardLoaded.topics`, `.strands`, `nodes[].topicId` (Task 4).

- [ ] **Step 1: Прочитать DESIGN_SYSTEM.md и colors.dart** (токены: цвета/радиусы/шрифты).

- [ ] **Step 2: Переписать `_GraphBody`**

Группировка: для каждого `strand` (по `strands`, отсортированы по `order`) → его темы (`topics` где `topic.strand==strand.code`, по `order`) → узлы темы (`nodes` где `node.topicId==topic.id`). Рендер: раздел (заголовок ru/kz + общий прогресс) → тема (название ru/kz, прогресс mastered/total, опционально мелкая подпись «← после: <названия тем-пререквизитов>») → строки навыков (существующий `_NodeRow`, переиспользовать). Legend сверху оставить. Узлы без `topicId` (если вдруг) — в раздел «Прочее». CC-коды НЕ показывать. Каждый уровень — состояния mastered/partial/failed/untested через существующие цвета.

- [ ] **Step 3: Локализация** — новые строки в `app_ru.arb` и `app_kk.arb` (например `graphPrereqLabel`), регенерация `flutter gen-l10n` если используется. Никаких хардкод-строк.

- [ ] **Step 4: Верификация**

Run:
```bash
cd frontend/apps/kodi_web && flutter analyze
flutter build web --release
```
Expected: 0 errors, build OK.

- [ ] **Step 5: Playwright-проверка**

Поднять backend (`cd backend && python run.py` со свежей/тестовой БД) + отдать собранный фронт; залогиниться тестовым юзером; открыть страницу графа. Через Playwright: navigate → snapshot → screenshot; консоль без ошибок. Убедиться: видна иерархия Раздел→Тема→навык, прогресс на уровнях.

- [ ] **Step 6: Коммит**

```bash
git add frontend/apps/kodi_web/lib/features/dashboard/pages/graph_page.dart frontend/apps/kodi_web/lib/l10n
git commit -m "feat: граф-страница рендерит иерархию Раздел→Тема→навык"
```

---

## Self-Review

**Spec coverage:**
- topics/topic_edges/node_topic данные → Task 1 ✓
- схема + идемпотентный bootstrap → Task 2 ✓
- API topics/strands/topic_id → Task 3 ✓
- фронт-иерархия + l10n → Tasks 4–5 ✓
- инварианты (118/118, 43/61, идемпотентность) → Task 1 + Task 2 тесты ✓
- контракт API → Task 3 тест ✓
- flutter analyze/build/Playwright → Task 5 ✓
- сверка выборки маппинга → Task 1 Step 3 (ручная проверка 12–15) ✓
- out-of-scope (118 узлов/движок не трогаем) → ни одна задача не меняет core/diagnostic|practice|exam|bkt ✓

**Type consistency:** `seed_topics(session)->int`, `Topic(id,strand,grade,order_idx,name_ru,name_kz)`, `GraphTopic{id,strand,nameRu,nameKz,grade,order,prereq,nodeIds}`, `topic_id`/`topicId` — согласованы между Task 2/3/4.

**Открытый риск:** имена разделов в API (Task 3 Step 3) — читать из `cc_topics_v01.json.strands`, не хардкодить; перепроверить при реализации.
