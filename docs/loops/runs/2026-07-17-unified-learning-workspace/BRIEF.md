# BRIEF — единый учебный workspace Kodi

## Результат

После выбора темы ребёнок работает в одном устойчивом пространстве: видит задачу, решает её на
бумаге или вводит ответ, получает контекстную AI-проверку, просит ровно столько помощи, сколько
нужно, и возвращается к самостоятельной transfer-задаче без ощущения перехода в другое
приложение.

## Аудитория и job-to-be-done

- Ученик 10–13 лет готовится к математическим блокам NIS.
- Он уже получил тему от маршрута и хочет понять: **что решать сейчас, как отправить решение и
  что исправить дальше**.
- Он может растеряться, не знать первый шаг, ошибиться, сделать нечёткое фото, потерять сеть или
  вернуться позже. Ни один из этих случаев не должен обнулять контекст.

## Главный продуктовый приоритет

Математика и самостоятельная попытка старше navigation, прогресса, brand и AI. AI не является
отдельным destination: он появляется рядом с той частью решения, где нужна помощь.

## UX-регистр

**Собранный.**

Он запрещает:

1. dashboard/card soup и каталог конкурирующих функций;
2. полноэкранную замену задачи при feedback, hint или открытии AI;
3. mascot-first, кислотную геймификацию и крупный декоративный display поверх математики.

Регистр помогает ребёнку за несколько секунд найти условие, свою попытку и одно следующее
действие, не превращая подготовку в официальный экзаменационный портал.

## Scope design-freeze

- устойчивый shell после `lesson_intro`;
- independent, submitting, feedback, recovery, guided, tutor, transfer и resume states;
- photo-default submission и typed alternative с одинаково server-owned semantic verdict;
- контекстный AI-assistant и progressive hint ladder;
- mobile 375×844 и desktop 1280×900;
- три структурно разные concept direction, browser evidence и выбор по frozen rubric;
- implementation backlog, связанный со state/API/test contracts.

## Не входит

- production React/backend diff, DB migration и deploy;
- redesign registration/diagnostic/route до начала темы, кроме continuity handoff;
- teacher/parent dashboard;
- новый персонаж или копия исходного логотипа;
- обещание learning gain без child usability и longitudinal data;
- изменение действующего `DESIGN_SYSTEM.md` до production render и отдельного READY.

## Product contracts

### 1. Stable geometry

После `Начать задачу` сохраняются четыре зоны:

- **task anchor** — тема, режим, условие и текущая работа;
- **session strip** — честный progress, сохранённость и выход без потери;
- **response dock** — photo default, typed alternative и текущая submit action;
- **contextual layer** — feedback, recovery, hint или tutor; он не заменяет task anchor.

Server `next_step` остаётся source of truth. Клиент не создаёт вторую stage-machine: он маппит
server stage на состояние четырёх зон.

### 2. Submission hierarchy

- `Фото решения` — основной путь для проверки хода: одно фото всей страницы остаётся доступной
  альтернативой до и после typed-проверки.
- `Ввести ответ` — постоянно видимая вторичная альтернатива. AI-confirmed `typed correct`
  атомарно завершает текущую задачу и открывает independent transfer-задачу (или topic result);
  фото после него не обязательно. `needs_revision` и `uncertain` оставляют ту же задачу, draft,
  typed, photo и help в доступе.
- Для одной самостоятельной задачи первый AI-confirmed `incorrect` и первый `correct` outcome
  учитываются по одному разу. Provider/transport error, uncertain, stale/superseded и replay не
  меняют mastery. Поддержанная практика (`support_used=true`) завершает шаг, но не даёт evidence;
  затем сервер открывает новую самостоятельную transfer-задачу.
- В guided mode используются text/options; фото каждого подэтапа не требуется.
- Один task имеет один draft namespace: фото, typed draft и tutor thread не перескакивают на
  другую identity/journey/problem.

### 3. AI-owned semantic verdict

- AI возвращает `correct | needs_revision | uncertain`, локализованный шаг, evidence,
  child-safe explanation и next action.
- Backend валидирует identity/auth/consent/idempotency/schema/enums/ranges/persistence и
  fail-closed recovery. Он не подменяет AI semantic verdict exact-string checker.
- Старое утверждение `docs/VISION.md` «правильность решает код» конфликтует с новым прямым
  owner decision. В этом run действует owner decision; implementation Goal обязан оформить ADR
  и синхронизировать vision/docs.

### 4. Context envelope

Backend строит trusted context проверки: `journey_id`, `revision`, learner/task identity, topic
goal, mode, server stage, full statement, canonical steps и accepted variants, correct answer как
hidden grounding, support state и bounded mastery evidence. Student submission и bounded history
этой же задачи — untrusted data в отдельном fenced блоке; они не могут переопределить инструкции
или grounding.

Hidden grounding не показывается ребёнку напрямую. Любой answer reveal маркирует попытку как
guided и требует новой transfer task.

### 5. Hint ladder

1. **Ориентир:** на что посмотреть в условии.
2. **Стратегия:** один Socratic question о следующем действии.
3. **Связь:** правило или модель без вычисленного ответа.
4. **Микро-шаг:** разобран один ближайший шаг после собственной попытки.

Следующий rung открывается только явно. Полный worked solution требует отдельного подтверждения,
не считается mastery и заканчивается новой independent transfer-задачей.

Открытие help/tutor не меняет eligibility. Получение первого содержательного hint/tutor response
ставит `support_used=true`, и текущая task становится practice-only. В transfer помощь остаётся
доступной, но её использование превращает transfer в supported practice и после разбора требует
новую transfer task.

### 6. Feedback grammar

- `correct`: что подтверждено → что делать дальше;
- `needs_revision`: где расходится ход → почему → исправить этот шаг;
- `uncertain`: что AI не смог надёжно увидеть/понять → переснять, ввести фрагмент или повторить
  проверку; это не математическая ошибка.

Legacy mapping не теряет причину: `unreadable | wrong_photo | unsure | provider_error` входят в
UX-family `uncertain` как `recovery_reason`; `incorrect` становится `needs_revision`.

Feedback короткий и action-oriented. Длинное объяснение открывается по запросу в tutor layer.

## Responsive behavior

### Mobile 375×844

- task anchor — основной scroll surface;
- response dock компактно закреплён снизу и не перекрывает focused control;
- feedback/hint/tutor открываются как sheet не выше необходимого, task context остаётся видимым;
- photo и typed mode переключаются без ухода со страницы;
- primary action находится в reach zone, все targets ≥44×44 px.

### Short landscape и keyboard: 844×375, 932×430

- typed form переходит в обычный document flow: fixed dock не обрезает input, submit или photo/help;
- интерактивные controls остаются видимы, доступны с keyboard и не создают horizontal overflow;
- после atomic typed advance focus переходит на heading новой задачи.

### Desktop 1280×900

- task/work занимают доминирующую рабочую область;
- contextual layer живёт в правом rail и не сжимает условие до mobile-card;
- response dock относится к task surface, а не к глобальной навигации;
- пустое пространство поддерживает focus, а не заполняется метриками/карточками.

## Required states

`independent`, `photo-selected`, `typed-draft`, `typed-advancing`, `submitting`, `correct`,
`needs_revision`, `uncertain`, `offline/provider-error`, `stale-server-state`, `hint-rung-1..4`,
`tutor-open`, `guided-step`, `transfer`, `topic-result`, `resume`.

## Accessibility and craft

- учебный текст ≥18 px; line-height достаточен для кириллицы и формул;
- target ≥44×44 px, видимый `:focus-visible`, logical tab order;
- local error identification + recovery action; status через `aria-live`;
- sticky dock не перекрывает focus; в short landscape typed form возвращается в document flow; no
  horizontal page overflow;
- reduced motion сохраняет причинность без обязательной анимации;
- цвет не является единственным носителем mode/verdict;
- проверяются реальные `Ә Ғ Қ Ң Ө Ұ Ү Һ І`, кириллица и дроби в выбранных fonts.

## Anti-reference

- действующая «Фокус-станция»: один full-screen state на этап и крупный display, конкурирующий с
  условием;
- старые отдельные `/drill`, `/review` и generic persistent chat;
- card grid, bottom navigation с каталогом функций, несколько primary CTA;
- огромные component shells, которые заставляют скроллить до ответа;
- mascot/brand как главный объект задачи;
- orange wall, candy palette, SaaS blue/glass и официальный школьный портал;
- hint, который сразу даёт вычисленный ответ.

## Success criteria

1. За 5 секунд понятны задача, режим и следующее действие.
2. При feedback/help условие не исчезает и режим не маскируется.
3. Photo default и typed alternative доступны в одном workspace; `typed correct` без фото
   открывает следующую server-owned задачу.
4. Один primary CTA, compact secondary controls, нет function catalog.
5. Resume восстанавливает task, draft, attempt, hint rung, feedback и tutor thread.
6. Все mechanics green на 375×844, 844×375, 932×430 и 1280×900.
7. Два blind reviewer дают `READY` по frozen bar без P0/P1.
