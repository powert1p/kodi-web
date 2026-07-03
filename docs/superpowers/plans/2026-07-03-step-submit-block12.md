# Implementation Plan — Block 1.2 «Поэтапная сдача» (step-submit)

**Spec:** docs/specs/2026-07-03-step-submit-block12.md
**Date:** 2026-07-03

## Goal
Реализовать поэтапную сдачу фото одного шага лесенки: FastAPI-эндпоинт классифицирует фото (match/mismatch/unsure), двигает существующую машину лесенки на клиенте, пишет каждую сдачу в датасет (`step_submissions` + фото). Owner-эндпоинты для выгрузки датасета.

## Architecture
- **Vision:** новая `classify_step_photo()` в `core/llm_openai.py` — узкая json_schema (verdict/seen_value/confidence), реюз всей инфраструктуры `diagnose_photo` (клиент, model_chain, strict-fallback, HEIC, `LlmUnavailable`, таймаут).
- **Handler:** `POST /api/trainer/step-submit` в `api/routers/trainer.py` — гейты как у `/diagnose`, порог confidence, fingerprint-hint, INSERT `step_submissions`, файл после commit.
- **Data:** таблица `step_submissions` (ORM-модель + идемпотентный CREATE в `run.py`), фото в `error_photos/steps/{student_id}/{uuid}.jpg`.
- **Frontend:** сегмент-контрол drill-уровня; в режиме «По тетради» активная original-ступень сдаётся через `useStepSubmitFlow`; вердикт мостится в существующий `drill.submit()` (ladder.ts НЕ меняем).
- **Telemetry:** существующий `track()` → события `hint_shown` / `step_mode_switched` / `step_photo_verdict` / `step_retry_after_unsure`.

## Tech Stack
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, `openai` SDK (Gemini openai-compat), slowapi (`limiter`), pytest + pytest-asyncio.
- Frontend: React + TS strict, TanStack Query, Tailwind v4, Ap*-компоненты (DESIGN_SYSTEM v5), vitest.

## Global Constraints
- Комментарии на русском, термины английские. Без новых зависимостей.
- SQL — только параметризованный (`text(":param")`); `IN`/массивы через `= ANY(:arr)` или `bindparam(expanding=True)`.
- Async всегда; сессия закрывается в `finally`; commit до записи файла.
- НЕ трогать `/diagnose`, `ladder.ts`-логику, чужой код. Никаких DROP/DELETE/TRUNCATE.
- Owner-гейт: `settings.owner_student_id != 0 and student.id == settings.owner_student_id`, иначе 403.
- Каждая задача заканчивается зелёными тестами + `flutter`-неприменимо (это React PWA `webapp/`, не Flutter): фронт-гейты = `pnpm tsc`, `pnpm lint:design`, `pnpm build`, vitest.

---

## Task 1 — Таблица `step_submissions` (модель + миграция)

**Files:** `backend/db/models.py`, `backend/run.py`, `backend/tests/test_step_submit_api.py` (новый — здесь только schema-тест).

**Interface (ORM, зеркалит стиль `ErrorCapture`/`Event`):**
```python
# backend/db/models.py — добавить после класса Event
class StepSubmission(Base):
    """Одна сдача фото шага лесенки (Блок 1.2). Датасет фото+шаг+вердикт."""

    __tablename__ = "step_submissions"
    __table_args__ = (
        Index("idx_step_submissions_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    decomp_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    step_n: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)  # match|mismatch|unsure
    confidence: Mapped[float | None] = mapped_column(Float)
    matched_micro_skill: Mapped[str | None] = mapped_column(String(50))
    photo_path: Mapped[str] = mapped_column(Text, nullable=False)     # относительно photo_dir
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False
    )
```

**Migration (`backend/run.py` — в список DDL-строк, рядом с events, после строки `idx_events_student_created`):**
```python
            """
            CREATE TABLE IF NOT EXISTS step_submissions (
                id                  BIGINT      PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                student_id          BIGINT      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                decomp_idx          INTEGER     NOT NULL,
                step_n              INTEGER     NOT NULL,
                problem_id          INTEGER     REFERENCES problems(id) ON DELETE SET NULL,
                verdict             VARCHAR(16) NOT NULL,
                confidence          FLOAT,
                matched_micro_skill VARCHAR(50),
                photo_path          TEXT        NOT NULL,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_step_submissions_student_created ON step_submissions (student_id, created_at)",
```

**TDD steps:**
1. В новом `backend/tests/test_step_submit_api.py` написать schema-тест по образцу `test_pilot_schema.py`: подключиться к `TEST_DATABASE_URL` (skip если нет), выполнить DDL из `run.py` (или вызвать существующую bootstrap-функцию), затем `SELECT column_name FROM information_schema.columns WHERE table_name='step_submissions'` → проверить набор колонок. Тест падает (таблицы нет).
2. Добавить модель + DDL. Тест зелёный.
3. `.venv/bin/pytest backend/tests/test_step_submit_api.py -x -q`.

**DoD:** таблица создаётся идемпотентно; schema-тест зелёный; существующие тесты не сломаны.

---

## Task 2 — `classify_step_photo()` (vision-классификация)

**Files:** `backend/core/config.py`, `backend/core/llm_openai.py`, `backend/tests/test_llm_openai.py`.

**Config (`config.py`, в dataclass `Settings`, рядом с `photo_dir`):**
```python
    # Порог уверенности для step-submit: mismatch с confidence ниже → трактуем как unsure
    step_confidence_threshold: float = float(os.getenv("STEP_CONFIDENCE_THRESHOLD", "0.6"))
```

**Interface (`llm_openai.py`):**
```python
@dataclass
class StepClassification:
    """Результат классификации фото одного шага лесенки."""
    verdict: str          # "match" | "mismatch" | "unsure"
    seen_value: str | None
    confidence: float


_STEP_JSON_SCHEMA = {
    "name": "step_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "seen_value", "confidence"],
        "properties": {
            "verdict": {"type": "string", "enum": ["match", "mismatch", "unsure"]},
            "seen_value": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "confidence": {"type": "number"},
        },
    },
}


def _build_step_prompt(*, statement: str, instruction_ru: str, expected_value: str) -> str:
    """Короткий промпт классификации одного шага (не транскрипция)."""
    stmt_part = f"ЗАДАЧА (контекст): {statement}\n\n" if statement else ""
    return (
        "Ты проверяешь фото ОДНОГО шага рукописного решения ученика.\n\n"
        f"{stmt_part}"
        f"ОЖИДАЕМЫЙ ШАГ: {instruction_ru}\n"
        f"ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ЭТОГО ШАГА: {expected_value}\n\n"
        "Классифицируй, есть ли на фото этот шаг с ожидаемым результатом:\n"
        "- \"match\": на фото виден шаг и его результат совпадает с ожидаемым.\n"
        "- \"mismatch\": шаг виден, но результат отличается от ожидаемого.\n"
        "- \"unsure\": не разобрать / на фото не этот шаг / вся страница целиком.\n\n"
        "seen_value — что ты прочитал как результат шага (или null). "
        "confidence — уверенность 0.0–1.0. Отвечай строго в JSON-схеме."
    )


async def classify_step_photo(
    *,
    image_bytes: bytes,
    content_type: str,
    statement: str,
    instruction_ru: str,
    expected_value: str,
) -> StepClassification:
    ...
```

**Реализация:** скопировать тело `diagnose_photo` (строки 261–374), заменив: промпт → `_build_step_prompt(...)`; схему → `_STEP_JSON_SCHEMA`; парсинг → `StepClassification(verdict=data["verdict"], seen_value=data.get("seen_value"), confidence=float(data["confidence"]))`. Сохранить: `_get_active_client()`, HEIC-конверсию (`_is_heic`/`_convert_heic_to_jpeg`), `data_url`, цикл по `model_chain`, `asyncio.wait_for(_OPENAI_TIMEOUT)`, gemini strict-fallback (тот же блок `if provider == "gemini" and "strict" in str(exc).lower()`), финальный `raise LlmUnavailable`. `max_tokens=256` (классификация короткая).

**TDD steps (в `test_llm_openai.py`, реюз `_make_fake_client`/`_TINY_PNG`/`_TEST_MODEL_CHAIN`):**
1. `test_classify_step_photo_match`: fake client payload `{"verdict":"match","seen_value":"115","confidence":0.9}`; `patch("core.llm_openai._get_active_client", return_value=(client, _TEST_MODEL_CHAIN))`; вызвать `classify_step_photo(...)`; assert `.verdict=="match"`, `.confidence==0.9`. Падает (функции нет).
2. Реализовать функцию + config-поле. Тест зелёный.
3. Добавить `test_classify_step_photo_mismatch` и `test_classify_step_photo_unsure` (verdict-эхо).
4. `test_classify_step_photo_strict_fallback`: fake client, у которого первый `create` бросает `Exception("strict not supported")`, второй возвращает payload; настроить `vision_provider="gemini"` через monkeypatch settings; assert результат распарсен (реюз паттерна strict-fallback теста для diagnose).
5. `test_classify_step_photo_llm_unavailable`: client где `create` всегда бросает → assert `pytest.raises(LlmUnavailable)`.
6. `.venv/bin/pytest backend/tests/test_llm_openai.py -x -q`.

**DoD:** 5 новых unit-тестов зелёные; порог НЕ применяется здесь (только парсинг).

---

## Task 3 — `POST /api/trainer/step-submit` + fingerprint-hint

**Files:** `backend/api/routers/trainer.py`, `backend/tests/test_step_submit_api.py`.

**Imports (в шапке trainer.py):** добавить `classify_step_photo, StepClassification` к импорту из `core.llm_openai`.

**Pydantic-схема ответа:**
```python
class StepSubmitOut(BaseModel):
    verdict: str            # match | mismatch | unsure
    hint: str | None        # mistake_ru при mismatch, иначе None (expected_value НЕ раскрываем)
    confidence: float
    step_n: int
```

**Endpoint (после `/diagnose`, паттерн гейтов оттуда):**
```python
@router.post("/step-submit", response_model=StepSubmitOut)
@limiter.limit("15/minute")
async def post_step_submit(
    request: Request,
    decomp_idx: int = Form(...),
    step_n: int = Form(...),
    problem_id: int | None = Form(None),
    photo: UploadFile = FastApiFile(...),
) -> StepSubmitOut:
    session, student = await _get_current_student(request)
    try:
        # 1. consent-гейт (как /diagnose)
        if student.photo_consent is not True:
            raise HTTPException(status_code=403,
                detail={"code": "consent_required",
                        "message": "Нужно согласие родителя на использование фото."})
        # 2. size/content-type гейты — СКОПИРОВАТЬ блок из /diagnose (413/415, content_type default jpeg)
        ...
        image_bytes = await photo.read()
        ... (пост-чтение 413)
        # 3. шаг из problem_steps (404 если нет)
        step_row = (await session.execute(
            text("SELECT n, instruction_ru, micro_skill, expected_value FROM problem_steps "
                 "WHERE decomp_idx = :d AND n = :n"),
            {"d": decomp_idx, "n": step_n},
        )).fetchone()
        if step_row is None:
            raise HTTPException(status_code=404,
                detail=f"Шаг {step_n} декомпозиции {decomp_idx} не найден")
        # 4. statement (контекст) — если problem_id задан
        statement = ""
        if problem_id is not None:
            prob = (await session.execute(
                text("SELECT text_ru FROM problems WHERE id = :pid"),
                {"pid": problem_id},
            )).fetchone()
            if prob is not None:
                statement = prob.text_ru
        # 5. классификация (LlmUnavailable → 503)
        try:
            cls = await classify_step_photo(
                image_bytes=image_bytes, content_type=content_type,
                statement=statement, instruction_ru=step_row.instruction_ru,
                expected_value=step_row.expected_value,
            )
        except LlmUnavailable as exc:
            raise HTTPException(status_code=503,
                detail="Сервис проверки фото временно недоступен. Попробуйте позже.") from exc
        # 6. порог: mismatch с низкой confidence → unsure (false-reject хуже пропуска)
        verdict = cls.verdict
        if verdict == "mismatch" and cls.confidence < settings.step_confidence_threshold:
            verdict = "unsure"
        # 7. fingerprint-hint только при mismatch
        hint: str | None = None
        matched_ms: str | None = None
        if verdict == "mismatch":
            fp = (await session.execute(
                text("SELECT mistake_ru FROM problem_fingerprints "
                     "WHERE decomp_idx = :d AND micro_skill = :ms LIMIT 1"),
                {"d": decomp_idx, "ms": step_row.micro_skill},
            )).fetchone()
            if fp is not None:
                hint = fp.mistake_ru
                matched_ms = step_row.micro_skill
        # 8. путь фото (относительно photo_dir): steps/{student_id}/{uuid}.jpg
        file_name = f"{uuid4().hex}.jpg"
        photo_path = f"steps/{student.id}/{file_name}"
        # 9. INSERT ВСЕГДА (включая unsure)
        await session.execute(
            text("INSERT INTO step_submissions "
                 "(student_id, decomp_idx, step_n, problem_id, verdict, confidence, "
                 " matched_micro_skill, photo_path, created_at) "
                 "VALUES (:sid,:d,:n,:pid,:v,:conf,:ms,:path,NOW())"),
            {"sid": student.id, "d": decomp_idx, "n": step_n, "pid": problem_id,
             "v": verdict, "conf": cls.confidence, "ms": matched_ms, "path": photo_path},
        )
        await session.commit()
    finally:
        await session.close()
    # 10. файл после commit (паттерн /diagnose: steps/{student_id}/)
    photo_dir = Path(settings.photo_dir)
    student_dir = photo_dir / "steps" / str(student.id)
    try:
        student_dir.mkdir(parents=True, exist_ok=True)
        (student_dir / file_name).write_bytes(image_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось записать фото шага (%s): %s", photo_path, exc)
    return StepSubmitOut(verdict=verdict, hint=hint, confidence=cls.confidence, step_n=step_n)
```
> Точный текст size/content-type блока (строки 375–410 в `/diagnose`) СКОПИРОВАТЬ без изменений, включая `_MAX_PHOTO_BYTES`, `_ALLOWED_CONTENT_TYPES`, дефолт `content_type = "image/jpeg"`.

**TDD steps (в `test_step_submit_api.py`, фикстура по образцу `client_for_diagnose`):**
1. Фикстура `client_for_step`: seed студент (photo_consent=true) + узел + задача + `decomposition_problems` (idx) + `problem_steps` (decomp_idx, n=1, instruction_ru, micro_skill='div_basic', expected_value='4') + `problem_fingerprints` (decomp_idx, micro_skill='div_basic', wrong_answer='8', mistake_ru='Забыл разделить на 2'); monkeypatch `photo_dir=tmp_path`; выдать токен; вернуть `(ac, student_id, token, decomp_idx, step_n, pid, tmp_path)`.
2. `_mock_classify(verdict, conf)` → monkeypatch `"api.routers.trainer.classify_step_photo"` (патчить ТАМ, где импортирован — как `diagnose_photo`).
3. Тесты (каждый падает → реализация → зелёный):
   - `test_step_submit_match`: mock verdict=match conf=0.9 → 200, `verdict=="match"`, `hint is None`; строка в `step_submissions` (`SELECT count(*)`=1); файл существует в `tmp_path/steps/{sid}/`.
   - `test_step_submit_mismatch_hint`: mock mismatch conf=0.9 → `verdict=="mismatch"`, `hint=="Забыл разделить на 2"`, `matched_micro_skill=='div_basic'` в БД.
   - `test_step_submit_low_conf_becomes_unsure`: mock mismatch conf=0.3 (порог 0.6) → `verdict=="unsure"`, `hint is None`; строка verdict='unsure' в БД.
   - `test_step_submit_unsure`: mock unsure → 200, hint None, строка есть.
   - `test_step_submit_consent_required`: студент с photo_consent=NULL → 403, detail.code=='consent_required'.
   - `test_step_submit_413`: photo с `size` > 8МБ → 413. `test_step_submit_415`: content_type 'text/plain' → 415.
   - `test_step_submit_503`: mock бросает `LlmUnavailable` → 503.
   - `test_step_submit_step_not_found`: несуществующий step_n → 404.
4. `.venv/bin/pytest backend/tests/test_step_submit_api.py -x -q`.

**DoD:** все integration-тесты зелёные; unsure пишет строку и НЕ создаёт attempts (проверить `SELECT count(*) FROM attempts`=0).

---

## Task 4 — Owner-эндпоинты: export CSV + step-photo

**Files:** `backend/api/routers/trainer.py`, `backend/tests/test_step_submit_api.py`.

**Interface:**
```python
@router.get("/step-submissions/export")
async def get_step_submissions_export(
    request: Request, format: str = Query("csv", pattern="^csv$")
) -> Response:
    """CSV-выгрузка step_submissions (мета). Только владелец, иначе 403."""
    # паттерн get_events_export: owner-гейт, SELECT всех строк, csv.writer
    # колонки: id, student_id, decomp_idx, step_n, problem_id, verdict,
    #          confidence, matched_micro_skill, photo_path, created_at


@router.get("/step-photo/{submission_id}")
async def get_step_photo(request: Request, submission_id: int) -> Response:
    """Фото сдачи по id. Только владелец (403). 404 если строки/файла нет."""
    session, student = await _get_current_student(request)
    try:
        is_owner = settings.owner_student_id != 0 and student.id == settings.owner_student_id
        if not is_owner:
            raise HTTPException(status_code=403, detail="Только для владельца")
        row = (await session.execute(
            text("SELECT photo_path FROM step_submissions WHERE id = :id"),
            {"id": submission_id},
        )).fetchone()
    finally:
        await session.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Сдача не найдена")
    file_path = Path(settings.photo_dir) / row.photo_path
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Файл фото не найден")
    return Response(content=file_path.read_bytes(), media_type="image/jpeg")
```
> owner-гейт ДО чтения photo_path (не палить существование строк не-владельцу).

**TDD steps:**
1. `test_step_export_owner_ok`: monkeypatch `owner_student_id=student_id`; после ≥1 сдачи → GET export → 200, `text/csv`, тело содержит заголовок и хотя бы 1 строку.
2. `test_step_export_forbidden`: `owner_student_id=0` (или чужой) → 403.
3. `test_step_photo_owner_ok`: сделать сдачу (файл записан), взять `id` из БД, owner → GET step-photo → 200, `image/jpeg`.
4. `test_step_photo_forbidden`: не-owner → 403.
5. `test_step_photo_404`: owner, несуществующий id → 404.
6. `.venv/bin/pytest backend/tests/test_step_submit_api.py -x -q`.

**DoD:** owner-гейт закрывает оба эндпоинта; 404-ветки покрыты.

---

## Task 5 — Frontend API + `useStepSubmitFlow` + телеметрия-типы

**Files:** `webapp/src/lib/api.ts`, `webapp/src/features/drill/useStepSubmitFlow.ts` (новый), `webapp/src/features/drill/mock.ts`, `webapp/src/lib/types.ts`.

**Types (`types.ts`):**
```ts
export type StepVerdictKind = 'match' | 'mismatch' | 'unsure'
export interface StepVerdict {
  verdict: StepVerdictKind
  hint: string | null
  confidence: number
  step_n: number
}
```

**API (`api.ts`, по образцу `postDiagnose`/`useDiagnose`):**
```ts
export interface StepSubmitParams {
  decomp_idx: number
  step_n: number
  problem_id?: number
  photo: File | Blob
}

export async function postStepSubmit(params: StepSubmitParams): Promise<StepVerdict> {
  const form = new FormData()
  form.append('decomp_idx', String(params.decomp_idx))
  form.append('step_n', String(params.step_n))
  if (params.problem_id !== undefined) form.append('problem_id', String(params.problem_id))
  form.append('photo', params.photo)
  const res = await apiFetch(`${API_BASE}/trainer/step-submit`, {
    method: 'POST', headers: authHeaders(), body: form,
  })
  return res.json() as Promise<StepVerdict>
}

export function useStepSubmit() {
  return useMutation({ mutationFn: (p: StepSubmitParams) => postStepSubmit(p) })
}
```

**Mock (`mock.ts`):**
```ts
import type { StepVerdict } from '../../lib/types'
export const MOCK_STEP_VERDICT: StepVerdict = { verdict: 'match', hint: null, confidence: 0.9, step_n: 1 }
```

**Hook (`useStepSubmitFlow.ts`, аналог `useDiagnoseFlow`):**
```ts
export type StepSubmitStatus = 'idle' | 'uploading' | 'submitting' | 'result' | 'error'
interface StepSubmitFlow {
  status: StepSubmitStatus
  verdict: StepVerdict | null
  needsConsent: boolean   // 403
  is503: boolean          // 503
  start: (file: File, args: { decomp_idx: number; step_n: number; problem_id?: number }) => Promise<void>
  reset: () => void
}
```
Реализация: `compressForUpload(file)` → `submit.mutateAsync({ ...args, photo })`; 403 → `needsConsent`; 503 → `is503`; DEV без бэка → `MOCK_STEP_VERDICT` после `MOCK_DELAY_MS`; ошибки → status `error`. (Скопировать структуру `useDiagnoseFlow`, заменив `diagnose`→`useStepSubmit`, `Diagnosis`→`StepVerdict`, добавив аргументы шага.)

**TDD steps (vitest, `webapp/src/test/useStepSubmitFlow.test.ts`):**
1. Мокнуть `postStepSubmit` (vi.mock '../lib/api') → вернуть mismatch с hint; вызвать `start` через `renderHook` + `act`; assert `status==='result'`, `verdict.hint` проброшен. Падает (файла нет).
2. Реализовать хук/api/типы/mock. Тест зелёный.
3. Тест 403 → `needsConsent===true`.
4. `pnpm --dir webapp test -- useStepSubmitFlow` + `pnpm --dir webapp tsc`.

**DoD:** хук возвращает вердикт/consent/503; tsc чист.

---

## Task 6 — UI: режим «По тетради» в drill (v5-протокол)

**Files:** `webapp/src/features/drill/StepModeToggle.tsx` (новый), `webapp/src/features/drill/StepSubmitPanel.tsx` (новый), `webapp/src/features/drill/DrillPage.tsx`, `webapp/src/features/drill/RungActive.tsx`, `webapp/src/features/drill/Ladder.tsx`, `webapp/src/lib/telemetry.ts` (только вызовы `track`).

**v5-эталон / макет (обязательно перед кодом):** читать `webapp/DESIGN_SYSTEM.md`. Toggle = сегмент-контрол на Ap-токенах (brand-заливка активного сегмента, `text-caption1-medium`, `rounded-control`, focus/hover-состояния). Панель сдачи = Ap-кнопка «Сфотать шаг N» (brand, full) + баннеры вердикта на существующих `HintBanner`-паттернах. Мобайл 390×844, `lint:design` зелёный.

**StepModeToggle.tsx (props):**
```ts
interface StepModeToggleProps { mode: 'input' | 'tetrad'; onChange: (m: 'input' | 'tetrad') => void }
```
Два сегмента «Ввод» / «По тетради»; `role="tablist"`, `aria-selected`; hover/focus/active-состояния.

**StepSubmitPanel.tsx (props):**
```ts
interface StepSubmitPanelProps {
  stepN: number
  status: StepSubmitStatus
  verdict: StepVerdict | null
  onPhoto: (file: File) => void
  onRetry: () => void   // reset flow для повторного фото
}
```
Рендер по `status`:
- `idle` → кнопка «Сфотать шаг {stepN}» (скрытый `<input type=file accept=image/* capture=environment>` как в `PhotoCapture`).
- `uploading|submitting` → индикатор «Кёди смотрит…».
- `result` + verdict==='mismatch' → `HintBanner` с `verdict.hint ?? 'Проверь этот шаг ещё раз'` (variant hint) + кнопка «Сфотать заново».
- `result` + verdict==='unsure' → `HintBanner` «Не разглядел — сфотай ещё раз, только этот шаг крупнее» (mood/variant thinking) + кнопка «Сфотать заново».
- `error` + needsConsent — обрабатывается в DrillPage через `ConsentCard` (как diagnose-путь).
> match НЕ рендерит баннер в панели (ступень уходит solved, панель перемонтируется на следующий шаг).

**DrillPage.tsx — `DrillContent` изменения:**
```ts
const [mode, setMode] = useState<'input' | 'tetrad'>('input')
const stepFlow = useStepSubmitFlow()
// активная original-ступень: photo-режим применим только к ней
const activeRung = drill.activeRung
const isOriginalActive = activeRung?.kind === 'original'
const photoMode = mode === 'tetrad' && isOriginalActive
const activeStepN = activeRung && activeRung.kind === 'original'
  ? Number(activeRung.key.slice(1))   // key = `s${n}`
  : null

// МОСТ вердикта в машину лесенки (эффект на смену stepFlow.verdict)
useEffect(() => {
  if (stepFlow.status !== 'result' || !stepFlow.verdict || !activeRung) return
  const v = stepFlow.verdict
  void track('step_photo_verdict', { verdict: v.verdict, decomp_idx: task.decomp_idx, step_n: v.step_n })
  if (v.verdict === 'match') {
    drill.submit(activeRung.expected_value)   // гарантированный correct — реюз climb-back/next
    stepFlow.reset()
  } else if (v.verdict === 'mismatch') {
    drill.submit('nomatch')             // гарантированный wrong — реюз climb-down/hint
    // stepFlow.reset() вызывается кнопкой «Сфотать заново» после показа hint
  } else {
    void track('step_retry_after_unsure')     // unsure: машину НЕ трогаем
  }
}, [stepFlow.status, stepFlow.verdict])       // eslint-disable-line — намеренно узкие deps
```
- Рендер тоггла: над `<Ladder>` внутри `hasSteps && !drill.finished` блока:
  `<StepModeToggle mode={mode} onChange={(m) => { setMode(m); void track('step_mode_switched', { mode: m }) }} />`
- Панель сдачи: под `<Ladder>`, только если `photoMode`:
  `<StepSubmitPanel stepN={activeStepN!} status={stepFlow.status} verdict={stepFlow.verdict}
     onPhoto={(f) => void stepFlow.start(f, { decomp_idx: task.decomp_idx!, step_n: activeStepN!, problem_id: task.problem_id })}
     onRetry={stepFlow.reset} />`
- Consent 403 в step-режиме: `stepFlow.needsConsent` → рендерить существующую `ConsentCard` (как в diagnose-ветке), `onGranted/onDismiss = stepFlow.reset`.

**Ladder.tsx / RungActive.tsx:** прокинуть `photoMode?: boolean` (Ladder → активный RungActive). В `RungActive`, если `photoMode` — НЕ рендерить `<form>`/choose-блок (инструкция шага остаётся видимой; ввод замещён панелью ниже). Одно условие `!photoMode && (...)` вокруг существующего блока ввода. Больше ничего в RungActive не менять.

**Телеметрия `hint_shown`:** в `RungActive`, где показывается `HintBanner` (socratic hint, строки 109–111) — добавить `useEffect`, шлющий `track('hint_shown')` при переходе `hint` false→true. Не дублировать на каждый рендер.

**TDD/проверка:**
1. `pnpm --dir webapp tsc` — типы чисты.
2. `pnpm --dir webapp lint:design` — зелёный.
3. `pnpm --dir webapp build` — проходит.
4. Playwright (dev :5173): drill → переключить «По тетради» → снимок 390×844 (сегмент активен, кнопка «Сфотать шаг 1», текстовый ввод скрыт) → соответствует v5.

**DoD (бинарно):** тоггл виден всегда, дефолт «Ввод»; в «По тетради» у active original-ступени форма ввода скрыта, показана кнопка «Сфотать шаг N»; easier-ступень сохраняет ввод; tsc/lint:design/build зелёные; скриншот снят.

---

## Task 7 — Интеграция + E2E + инварианты

**Files:** — (проверочная задача, правки только если что-то из DoD не держится).

**Steps:**
1. `.venv/bin/pytest backend/tests/ -x -q` — всё зелёное (новые + существующие ~98).
2. `pnpm --dir webapp tsc && pnpm --dir webapp lint:design && pnpm --dir webapp test && pnpm --dir webapp build`.
3. E2E локально (backend + vite): войти в drill → «По тетради» → сфотать шаг:
   - mock/real **match** → активная ступень становится solved, активируется следующая.
   - **unsure** (замокать/подсунуть непонятное фото) → баннер «сфотай ещё раз», wrongStreak НЕ вырос, `step_submissions` строка verdict='unsure', `attempts` без новой строки.
   - **mismatch** → баннер с fingerprint-hint (без expected_value), при 2-й mismatch — climb-down easier-ступень.
4. SQL-инварианты (против TEST/dev БД):
   - `SELECT count(*) FROM step_submissions` == числу выполненных сдач в сценарии.
   - `SELECT count(*) FROM step_submissions WHERE verdict='unsure'` ≥ 1 и соответствующих строк в `attempts` за сессию НЕ прибавилось.
5. Owner: `GET /api/trainer/step-submissions/export` под owner-токеном → CSV со строками сценария; `GET /api/trainer/step-photo/{id}` → 200 image/jpeg.

**DoD:** все критерии успеха из спеки выполнены; инварианты держатся; скриншот v5 приложен.

---

## Заметки для имплементатора
- `_MAX_PHOTO_BYTES`, `_ALLOWED_CONTENT_TYPES`, дефолт content_type, паттерн «файл после commit» — БРАТЬ дословно из `/diagnose` (trainer.py:375–410, 555–570), не переизобретать.
- `classify_step_photo` — копия структуры `diagnose_photo`; расхождение только в промпте/схеме/парсинге/`max_tokens`.
- Порог применяется ТОЛЬКО в роутере (шаг 6), НЕ в vision-функции.
- НЕ менять `ladder.ts`: мост через `drill.submit(expected_value)` / `drill.submit('nomatch')`.
- Ко ВСЕМ вердиктам пишется строка `step_submissions` (включая unsure) — не только к mismatch.
- НЕ добавлять доработки сверх перечисленного (no polish смежного кода, no новые эндпоинты/поля).
