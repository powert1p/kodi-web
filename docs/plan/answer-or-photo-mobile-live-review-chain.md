# Project Brief

Source path: `/Users/esetseitkamal/kodi-web/docs/plan/2026-07-20-answer-or-photo-mobile-live-review-source.md`
Source SHA-256: `ede79392f050a433dc882109a27e12f92980fd2bf83e0c13062e7be3f0642c18`

Brief служит индексом. При расхождении или пропуске авторитетен verbatim source.

## Outcome

В production ребёнок решает задачу в одном устойчивом workspace и может завершить её либо правильным AI-проверенным typed-ответом, либо фото решения. Каждый tap даёт немедленную и честную обратную связь, а mobile 375×844 не ломает математику, controls и переход к следующему шагу.

## Frozen product decisions

- DEC-001 [source:L8-L12] Правильный typed-ответ является полноценной сдачей: он завершает текущую задачу и открывает следующую без обязательного фото.
- DEC-002 [source:L8-L12] Фото остаётся равноправным альтернативным способом сдачи, а не обязательным доказательством после typed-ответа.
- DEC-003 [source:L19-L29] Семантический verdict ответа принадлежит grounded AI; backend валидирует контракт, state и safety, но подменяет AI exact-answer скриптом.

## Requirement registry

- REQ-001 [source:L1-L6] Любой submit tap меняет видимое состояние не позже 100 ms: pending/disabled показывается до success или локальной recoverable error. Double-submit, stale revision, timeout, offline и provider error не пропадают без обратной связи и не дублируют прогресс.
- REQ-002 [source:L8-L12] AI-проверенный correct exact и mathematically equivalent typed-ответ атомарно закрывает task, сохраняет попытку и переводит ребёнка к следующей задаче. Incorrect и uncertain сохраняют контекст и дают понятное следующее действие.
- REQ-003 [source:L8-L12] Photo submission и typed submission доступны на том же task surface без route jump; выбор одного не блокирует второй до финальной сдачи.
- REQ-004 [source:L14-L17] Mobile 375×844 и landscape не имеют page-level horizontal overflow, overlap с sticky/safe-area/keyboard, обрезанной математики или controls меньше 44×44 px. Первый viewport сохраняет task, одно primary action и видимый способ переключить typed/photo.
- REQ-005 [source:L17-L17] Все найденные на live review P0/P1 в submit flow и мобильном workspace либо исправлены, либо явно вынесены как реальный blocker с evidence; cosmetic P2 не подменяет functional acceptance.
- REQ-006 [source:L19-L21] AI-проверка получает journey/task identity, текущий stage, полное условие, canonical steps/accepted variants, hidden correct grounding, ответ ребёнка и историю текущего решения, чтобы verdict был контекстным.
- REQ-007 [source:L23-L29] Typed verdict в production получается от AI-ответа по validated schema; локальные arithmetic, string и format scripts не могут переопределить semantic result.

## Milestone graph

- M-001 requires: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007; result: на disposable learner воспроизведены submit и mobile сбои, зафиксирован новый answer-or-photo state/API/UX contract и executable acceptance matrix.
- M-002 requires: REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-007; after: M-001; result: contract реализован в backend/frontend с regression tests, зелёными gates и real renders; fresh blind reviewer не нашёл P0/P1 или единственная delta закрыта.
- M-003 requires: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005; after: M-002; result: exact candidate развёрнут без затрагивания learner data/tunnel, public typed/photo CJM и mobile live review зелёны, а rollback зафиксирован.

## Acceptance bar

- BAR-001 [source:L1-L6] В живом browser нет tap, после которого визуально «ничего не происходит»; network, console и server evidence совпадают с показанным state.
- BAR-002 [source:L8-L12] После AI `correct` typed-ответа виден success и новая task; CTA «отправь фото, чтобы завершить» для этой же task отсутствует.
- BAR-003 [source:L14-L17] Собственный осмотр и fresh live reviewer подтвердили 375×844, mobile landscape и 1280×900: нет P0/P1, overflow/overlap, потери focus/draft/context, console/request errors и непонятного next action.

## Constraints and prohibitions

- BAN-001 [source:L1-L6] Не считать unit/API tests заменой полного живого flow в browser.
- BAN-002 [source:L8-L12] Не требовать фото после правильного typed-ответа и не держать ребёнка на той же task.
- BAN-003 [source:L23-L29] Не добавлять authoritative arithmetic/exact-string fallback для semantic verdict и не показывать hidden answer в hint/feedback.
- BAN-004 [source:L14-L17] Не маскировать mobile-поломку desktop-only screenshot или косметическим reskin.

## Required artifacts

- ART-001 [source:L1-L6] Live reproduction packet: скриншоты 375×844/1280×900, tap timeline, request/response, console и server-log evidence для silent/stale/error paths.
- ART-002 [source:L8-L17] Frozen state/API/UX contract, file boundaries и executable acceptance matrix для typed exact/equivalent/incorrect/uncertain, photo, stale/offline/provider error и responsive states.
- ART-003 [source:L17-L17] Mechanical gate logs, before/after renders, own-eyes review, fresh blind review, public CJM/live-review report, exact image fingerprint и rollback receipt.

## Open decisions

- none

## Source coverage

- SRC-001 [source:L1-L4] → REQ-001, BAR-001, BAN-001, ART-001
- SRC-002 [source:L6-L6] → REQ-001, M-001, BAR-001
- SRC-003 [source:L8-L12] → DEC-001, DEC-002, REQ-002, REQ-003, BAR-002, BAN-002, ART-002
- SRC-004 [source:L14-L15] → REQ-004, BAR-003, BAN-004, ART-002
- SRC-005 [source:L17-L17] → REQ-005, M-001, M-002, M-003, BAR-003, ART-003
- SRC-006 [source:L19-L21] → DEC-003, REQ-006, M-001, M-002, ART-002
- SRC-007 [source:L23-L29] → DEC-003, REQ-007, M-001, M-002, BAN-003, ART-002
