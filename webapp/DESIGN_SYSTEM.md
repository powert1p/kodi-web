# DESIGN SYSTEM v11 — «Лента решения»

> Действующий канон React PWA `/app/`, 2026-07-15. Он принят из clean-slate run
> `docs/loops/runs/2026-07-15-webapp-v11-squirrel-clean-slate/`.
> V7–V10, точный logo lockup и костюм-лис — anti-reference, не источник решений.

## 1. Характер

AiPlus — тёплая математическая мастерская для ребёнка 10–13 лет после живого урока.
Интерфейс бодрый и тактильный, но не инфантильный; дорогой, но не официальный. Главный объект
каждого учебного экрана — конкретное математическое действие ученика.

Визуальная формула: **тёплая бумага + forest ink + дисциплинированный orange + функциональная
лента шагов**. Sage создаёт спокойный support-layer. Цвет и белка объясняют контекст, но не
соревнуются с условием, вводом и feedback.

## 2. Источники правды

- Product truth: `../docs/VISION.md` и frozen `BRIEF.md` активного run.
- Цвет, type tokens, radii, shadows: `src/theme/tokens.css`.
- Self-hosted fonts: `src/theme/fonts.css`.
- Math overflow, materials, focus, motion: `src/index.css`.
- UI contracts: `src/components/Ap*.tsx`, `BrandMark.tsx`, `Mascot.tsx`, `MathText.tsx`.
- Production harness: `../docs/loops/runs/2026-07-15-webapp-v11-squirrel-clean-slate/render_matrix.py`.

Сырые hex и arbitrary raw color/px values вне theme запрещены; смысловые `clamp()` и grid-
шаблоны допустимы. Контракт проверяет `npm run lint:design`.

## 3. Brand и персонажи

- `BrandMark` — самостоятельный code-native seed-mark: organic forest shape, строчная `a`,
  orange leaf/plus. Исходный прямоугольный логотип нельзя вставлять или трассировать.
- Wordmark остаётся текстом AiPlus, но не повторяет исходную композицию и эмблему.
- Используются только иллюстрированные белки из пользовательской Drive-папки, оптимизированные
  как `src/assets/brand/squirrel-*.webp`.
- Одна иллюстрация максимум на viewport. В active Drill/Srez белки нет.
- Login показывает учебный контекст; Hub — отдельную contextual note; celebrate — только после
  подтверждённого результата. Белка не является avatar AI-чата и не перекрывает контент.

## 4. Типографика и математика

- **Onest Variable** — весь интерфейс, инструкции, длинные условия и заголовки.
- **Tektur Variable** — только короткие marks, progress-числа, step nodes и интерактивное
  `Ответ = [ ]`. Длинная проза в Tektur запрещена.
- **Golos Text** — glyph fallback для кириллицы и казахского.
- KaTeX живёт внутри строки чтения. Формула не получает декоративный pill.
- Смешанная проза переносится естественно; только реально длинная формула получает локальный
  horizontal scroller с keyboard-доступом. Page-level overflow запрещён.

## 5. Цвет и материал

- Base: warm paper `--paper`, near-white `--surface`, deep forest `--ink`.
- Brand orange — CTA, active route node, progress event и небольшие labels. Orange wall нет.
- Sage — спокойный контекст/поддержка. Green — подтверждённый шаг. Oxide — локальная ошибка.
- Основной материал — открытая бумажная плоскость с редким grain, тонким stroke и мягкой тенью.
- Notches допустимы только у главной route-card Hub. Повторять их на каждой карточке нельзя.
- Card soup, bento, glass, generic AI gradient, SaaS blue и тёмный luxury-stage запрещены.

## 6. Signature: Solution Tape

Сквозная подпись отражает реальные данные решения:

1. Orange node показывает активный шаг.
2. Верный ответ фиксируется в green node и сохраняет введённое значение.
3. Следующий node открывается только после результата.
4. После второй ошибки один раз вставляется облегчённая ступень, затем маршрут возвращается к
   исходному шагу.
5. Hub показывает реальную очередь, Drill — полную функциональную ленту, Closure подтверждает
   перенос на новой задаче.

`Ответ = [ ]` — action-состояние внутри ленты, а не самостоятельный декоративный мотив.

## 7. Композиция

- Mobile 320–375 px — основной режим: math/task выше вводного текста, touch targets ≥44 px,
  input ≥16 px, bottom nav только «Путь» и «Прогресс».
- Корневой экран — накопительный «Мой путь»: курс → текущий учебный блок → один следующий урок.
  Дневная очередь «Сегодня» и закрытие ошибок как главная модель — anti-reference.
- Desktop ≥1024 px — самостоятельная композиция, не растянутый mobile stack.
- Hub: первая реальная задача и CTA командуют первым viewport; intro вторичен; белка находится в
  отдельной contextual note.
- Drill: активная операция и answer slot выше fold. Исходная задача доступна в compact disclosure;
  помощь и теория вторичны. Один global progress плюс локальная route node.
- Srez/Closure: короткий briefing, затем один вопрос и одно действие без persistent navigation.
- Analytics: открытый ranking накопленных повторений, не mastery, оценка или leaderboard.
- Login: спокойная форма + отдельная учебная иллюстрация; mascot не залезает в form-layer.

## 8. UX и state grammar

- Loading сохраняет геометрию. Error объясняет, что сохранилось, и даёт recovery. Empty не
  обещает mastery. Success показывает доказательство, а не случайное конфетти.
- Wrong меняет только ближайший slot/hint; правильный ответ не раскрывается.
- Srez не auto-advance. Closure решает только server-side; network error сохраняет input.
- `got` означает «Уверенно», не «Закрыто». Fake duration, fake progress и internal id запрещены.
- На protected page ровно один `<main id="main-content">`; skip-link и keyboard focus видимы.
- Normal motion показывает причинность `active → solved → next`; reduced motion сразу показывает
  то же конечное состояние без потери информации.

## 9. Production gates

```bash
npm run lint
npm run lint:design
npx tsc -b
npx vitest run
npm run build
```

Затем обязателен реальный render 375×844 и 1280×900 по state matrix: console/request errors,
overflow, fonts/images, touch, keyboard focus, loading/error/empty/success, wrong/network-preserve,
normal/reduced motion и mascot budget.

Frozen READY: mechanical gate green; у каждого из трёх независимых judges каждая ось ≥8,
average ≥8.5, `math_focus` и `premium_distinctiveness` ≥8.5; минимум 2/3 дают `wow`; нет
consensus high blocker.
