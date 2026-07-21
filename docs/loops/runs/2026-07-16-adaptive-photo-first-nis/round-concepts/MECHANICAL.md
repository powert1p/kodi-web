# Mechanical gate — concept round

Финальный immutable evidence: `evidence/SHA256SUMS` — 20 Chromium renders.

Проверка выполнена реальным Chromium через `agent-browser` для всех концептов и состояний на 375×844 и 1280×900. У принятого концепта C дополнительно проверен recovery-state.

Проверено:

- `documentElement.scrollWidth <= innerWidth` и bounding boxes всех видимых элементов;
- browser console и page errors;
- все видимые interactive targets не меньше 44×44 px;
- accessible name у каждого button/link/input/summary;
- реальный Tab order и `:focus-visible`, включая focus ring вокруг числового input;
- `role="alert"` + `aria-live="assertive"` в локальном photo-recovery;
- сохранение предыдущего photo evidence и одна локальная primary recovery-action;
- local font loading до измерений;
- `prefers-reduced-motion`: animation/transition duration ограничены 0.01 ms;
- responsive render route/photo/guided и recovery.

Результат acceptance-delta прогона:

```text
pages=20
failed_pages=0
horizontal_overflow=0
small_targets=0
unnamed_interactives=0
console_errors=0
page_errors=0
```

До финального прогона закрыты: mobile overlap маршрута, чрезмерно конкурирующая декоративная линза на задаче, слабая иерархия блока/темы, скрытая ниже первого viewport оговорка mastery и отсутствие локального recovery с сохранённым фото.
