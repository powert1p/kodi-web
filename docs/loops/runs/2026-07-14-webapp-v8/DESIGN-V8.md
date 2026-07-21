# Kodi Web V8 — Proof Pulse

## Тезис

**Мысль становится видимой.** Интерфейс показывает не абстрактный progress, а путь от
условия к конкретному месту сбоя и следующему самостоятельному действию.

Регистр: энергичный интеллектуальный инструмент для 10–13 лет. Не dashboard, не тетрадь,
не festival/esports и не детская игра.

## Палитра

- `cobalt #2233C7` — основная сцена и связь между экранами.
- `cobalt-deep #111B81` — briefing, navigation и спокойные dark planes.
- `bone #F4F1E8`, `bone-hi #FFFEF8` — рабочая поверхность.
- `ink #151A29` — основной текст на светлом.
- `blue-muted #C8CFFD` — secondary text на cobalt.
- `volt #D7F83A` — только active node и primary action.
- `tangerine #FF7A23` — только персонаж Кёди.
- `success #23865B`, `attention #9A6413` — semantic states без красного.

Сильная цветовая масса на экране одна. Functional text не приглушается opacity.

## Типографика

- **Tektur Variable**: logo, короткие labels, цифры, короткие screen anchors до шести слов.
- **Onest Variable**: весь интерфейс, условия, инструкции, feedback и длинные headings.
- **Golos Text**: glyph fallback для расширенной кириллицы/казахского.
- Учебный текст 18–20 px; form controls минимум 16 px; touch target минимум 44 px.

## Signature: ProofTrace

Один компонент, четыре честных режима:

- `queue`: один break node на каждую реальную задачу; active — первая задача очереди.
- `steps`: один node на каждую реальную ступень; active/solved/locked берутся из ladder.
- `check`: одна current mark с подписью `position / total`; это не fake progress mastery.
- `closure`: trace замыкается только после server-side verification.

Path рисуется один раз при входе (620 ms), active node фиксируется вторым коротким reveal.
При `prefers-reduced-motion` сразу показано конечное состояние. Infinite motion запрещён.

## Пространственные модели

### Hub

Full-bleed cobalt scene. Первый viewport — split между обещанием/CTA и светлой оптической
линзой с реальным `queue` trace. Очередь ниже — rule-based rows, не card stack.

### Drill

Focus mode без global navigation. Desktop: deep-cobalt briefing слева, bone workspace справа.
Mobile: briefing становится компактным верхним контекстом, workspace — основной экран.
`steps` trace проходит сквозь реальные rung states. «Метод» и «Спросить Кёди» вторичны.

### Srez

Focus mode. Volt index plane показывает честное `position / total`; cobalt work plane содержит
один вопрос, input и CTA в первом viewport. Нет correct answer на клиенте.

### Closure

Focus mode. Новая задача на bone; trace остаётся незамкнутым до правильного server verdict.
Celebration подтверждает самостоятельную проверку, не выдаёт вымышленный mastery.

### Analytics

Cobalt header + typographic ranking rows. Только error counts и last cause; без decorative
percent bars и обещания, что resolved автоматически исчезнет, пока API этого не гарантирует.

### Login

Cobalt visual field с project-local optical asset и proof trace; form живёт на bone. Progress
регистрации — реальные 3 шага, не gamified journey.

## Navigation

- Global: только `Сегодня` (`/`) и `Прогресс` (`/analytics`).
- Desktop: top navigation. Mobile: two-item bottom navigation с safe-area inset.
- `/drill`, `/closure`, `/srez`: focus mode без persistent navigation, явный back action.

## States

Loading сохраняет геометрию экрана. Empty объясняет следующий доступный action. Error всегда
содержит recovery. `unsure` означает «не разглядел — перефотай», не wrong. Focus ring 3 px,
keyboard navigation и `aria-live` обязательны. Горизонтальный overflow запрещён на 375 px.
