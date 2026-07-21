# DESIGN v7 — «Разбор по делу»

## Register lock

**Регистр:** editorial training desk — умный, энергичный и собранный интерфейс личного тренера по математике.

Запрещённые дефолты:

1. Тетрадная клетка на всей странице + кремовые карточки одинакового веса.
2. Гигантский Unbounded, двухстрочные uppercase-eyebrow и декоративный маршрут на каждом экране.
3. Kiddie/clay, dark premium, purple SaaS, «игра вместо учёбы».

## Направление

- Светлая бумага — фон, но не тема. Главный контраст создают тёплые чёрные чернила, белые рабочие поверхности и kodi-orange как единственный action accent.
- Композиция не «мобильная колонка посреди desktop»: на ≥1024px появляется навигационная rail и рабочая двухколоночная сцена; на mobile остаётся одна ясная колонка.
- QARA влияет на решительность type scale, асимметрию и плотность первого кадра. Industrial/neon/фестиваль не переносятся.

## Typography

- Display: **Alumni Sans** 700–900, self-hosted и проверенный на кириллице + `Ң`; используется для коротких заголовков и чисел.
- Body: **Golos Text** 400–700 для задач, форм, реплик Кёди.
- Длинные темы — sentence case. Uppercase допустим только для коротких service marks до 16 символов.
- Учебный текст 18–20px; secondary не меньше 13px; line length desktop 55–72 символа.

## Signature

**Progress rail / «поле разбора»** — функциональная координатная полоса, а не рисунок маршрута:

- hub: число оставшихся + очередь ошибок; активная ошибка помечена индексом;
- srez: `вопрос N / total` и честные сегменты;
- drill: `шаг N / total`, rail связан с активной ступенью;
- closure: один финальный checkpoint;
- login: rail отсутствует до тех пор, пока реального multi-step прогресса нет.

На desktop rail живёт слева от рабочей сцены; на mobile становится компактной горизонтальной status strip. Никаких флагов/точек без данных.

## Page contracts

### App shell

- Mobile: compact top brand + bottom navigation `Разбор / Срез / Прогресс`.
- Desktop: fixed-width left navigation rail, main canvas до 1120px; bottom bar превращается в sidebar.
- Main content всегда имеет safe inset под mobile nav; интерактив может быть проскроллен выше неё.

### Hub

- Первый кадр: editorial hero с честным count, короткой репликой и CTA «Начать разбор».
- Очередь задач — самостоятельные строки/панели, без общей декоративной spine.
- Consent не конкурирует с primary flow и явно просит передать устройство родителю.

### Drill

- Desktop: sticky briefing слева (topic/progress/Kodi), работа справа (условие → теория → active step).
- Mobile: compact header, task, текущий step; locked steps визуально тише.
- Page-level loading/error/not-found используют skeleton/retry/back, не голую строку.

### Srez

- Один вопрос на экране; поле и CTA визуально связаны с условием.
- Feedback не исчезает по таймеру: ученик сам нажимает «Следующий вопрос».

### Closure / Analytics / Login

- Closure — ясный checkpoint, без пустой нижней трети; pending ответа виден.
- Analytics — editorial list с реальными count, без дублирующей route spine.
- Login — mascot + форма; progress rail только на трёх реальных шагах регистрации.

## Motion and states

- 180–260ms, transform/opacity; один entrance sequence на страницу.
- `prefers-reduced-motion` мгновенно показывает финальное состояние.
- Hover, pressed, disabled, focus-visible обязательны; async CTA блокируется и показывает progress.

## Assets

Новые изображения в первом раунде не обязательны: предмет продукта — сама задача и процесс разбора. Существующие desk-assets можно использовать только как restrained texture. Если визуальная панель признает первый кадр плоским, следующий раунд добавляет один предметный asset, а не фото-декор на каждый экран.

