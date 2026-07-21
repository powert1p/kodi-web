# Design flow v3.2 — kodi-web

Это адаптация решения владельца от 2026-07-15 для Codex и mobile learning product. Переносится
**механика работы**, а не визуальный стиль какого-либо Claude artifact или лендинга.

## 1. Иерархия истины

1. Намерение владельца и `docs/VISION.md` определяют продукт.
2. Реальное поведение и данные приложения — обязательные invariants.
3. Для maintenance текущий `webapp/DESIGN_SYSTEM.md` — визуальный канон.
4. Для явного redesign или rejection текущего вида старая DS, компоненты, DOM и screenshots —
   только behavior evidence и **anti-reference**. Новым временным каноном становятся frozen
   brief + rubric + generator packet конкретного run'а.
5. `webapp/DESIGN_SYSTEM.md` обновляется только после победившего production render и READY,
   никогда по одному намерению или mockup.

## 2. Routing: два разных режима

| Сигнал | Режим | Полный loop |
|---|---|---|
| Исправить компонент, state или экран в принятой DS | Known-shape pipeline | Нет |
| Новая feature с ясной формой и DoD | Known-shape pipeline | Нет |
| «Дизайн ужасен», clean slate, неизвестно направление | Generator benchmark | Да |
| «До планки», «дорогой», «супер», нужны варианты | Generator benchmark | Да |
| Два подряд rejected acceptance pipeline | Generator benchmark | Да |

Known-shape pipeline: текущий Codex делает связный diff → запускает все gates и реальные
renders → один blind acceptance review → максимум одна delta. Два failed acceptance pipeline
подряд явно эскалируют работу в generator-loop; третьего круга косметики нет.

Generator benchmark следует `benchmark-loop`: ниже описана kodi-specific часть входа.

## 3. Generator packet до production-кода

### 3.1 Truth packet

- задача пользователя в одном предложении;
- аудитория и главный job-to-be-done экрана;
- реальные states и данные, которые нельзя потерять;
- устройства: 375×844 и 1280×900;
- performance, accessibility и product constraints;
- список rejected-паттернов из owner feedback и предыдущих run'ов.

### 3.2 Register lock

До концептов зафиксировать:

- **одно слово-регистр**, описывающее эмоциональный тон;
- 2–3 default tendency, которые этот регистр запрещает;
- почему это помогает ребёнку видеть математику, действие и feedback.

Пример формы, не готовое решение: `собранный`; запрещает dashboard-card soup, кислотную
геймификацию и декоративного mascot в роли главного объекта.

### 3.3 Три направления

До React production сравнить минимум три renderable spatial/art direction. Они обязаны
различаться одновременно по:

- spatial model и иерархии первого viewport;
- типографической системе;
- atmosphere/material/depth;
- одной сквозной signature.

Три палитры, три radius или новый font поверх старого DOM — один вариант и провал concept gate.
Владелец не обязан выбирать между промежуточными вариантами: frozen rubric выбирает лучший,
если не возникло материального product decision.

### 3.4 Seven-line shape plan

Каждый direction до build получает ровно этот shape packet:

1. register + запрещённые defaults;
2. направление и spatial model;
3. display/body fonts;
4. palette с hex и ролями;
5. одна signature;
6. image/asset count, placement и source;
7. layout, density и rhythm.

## 4. Перевод landing-механики в продукт

| Landing flow | kodi-web |
|---|---|
| Hero | Первый viewport каждого ключевого route |
| Signature в трёх scroll points | Одна signature через Hub → Drill → Srez/Closure |
| Mid-page cinematic punch | Режиссированный feedback/transition learning-flow |
| Обязательная фотография | Custom asset только если усиливает смысл; математика остаётся фокусом |
| Parallax/counters | Causal state motion, interruptible и reduced-motion safe |
| Storytelling scroll | Ясная задача → действие → проверка → следующий шаг |

Mascot не является signature сам по себе и не должен конкурировать с условием, формулой или
ответом. Brand orange — управляемый signal, а не заливка всех поверхностей.

## 5. Assets и typography gate

- Raster создаёт корневой Codex через встроенный `imagegen`; внешний `codex exec`, stock и
  placeholder blobs запрещены.
- Каждый generated asset сначала визуально осматривается. Несоответствие register/composition
  → regeneration, максимум три попытки до пересмотра prompt/direction.
- Серия ассетов строится от одного принятого reference, чтобы не распадался art direction.
- Display и body — разные роли, не обязательно разные семьи. До выбора проверяются реальные
  Cyrillic и казахские glyphs: `Ә Ғ Қ Ң Ө Ұ Ү Һ І`.
- Photo grade, overlays и UI palette должны принадлежать одной системе.

## 6. Production round

1. Победивший concept переносится в React без возврата к старому DOM только ради скорости.
2. Signature командует первым viewport, честно живёт минимум в трёх product states и не
   исчезает на mobile/reduced-motion.
3. Математический текст ≥18px, touch target ≥44px, один primary action на экран; error red не
   используется как brand/decor.
4. Loading, error, empty, success, long-content и keyboard states проектируются, а не
   достраиваются после happy path.
5. Motion объясняет причинность и состояние; decorative motion не задерживает действие.

## 7. Evidence до judging

Порядок нельзя менять:

1. `npm run lint`;
2. `npm run lint:design`;
3. `npx tsc -b`;
4. `npx vitest run`;
5. `npm run build`;
6. реальные renders 375×844 и 1280×900 по frozen state matrix;
7. console, horizontal overflow, keyboard, touch и reduced-motion;
8. собственный визуальный осмотр корневым Codex;
9. immutable evidence snapshot;
10. blind jury.

`NOT_RUN`, timeout и `BLOCKED` не равны PASS. Visual claim по одному коду не принимается.

## 8. Jury, delta и hard bar

- Для concept/smoke round нужны минимум два независимых native Codex judge. Для production
  redesign обязательны **три**; недоступный третий judge = `BLOCKED`, не fallback до двух.
  Maker не judge.
- Все получают один frozen rubric/snapshot и не видят прошлые scores или verdict коллег.
- Round 1 оценивается абсолютно. Round 2+ — blind randomized A/B против best-so-far;
  финальный кандидат получает absolute rescore.
- Если project rubric не строже: каждая из 8 осей ≥8.0, среднее ≥8.5,
  `visual_punch/signature` ≥8.0, critical detector flags = 0.
- READY требует явный verdict `READY` от каждого обязательного judge. Mixed, absent,
  `NOT_YET` или `UNCERTAIN` не проходят terminal gate даже без заполненной blocking delta.
- Budget или plateau двух раундов ниже bar = `NOT_READY/UNCERTAIN`, никогда `READY`.

## 9. Чинится генератор, не только output

После `NOT_YET`:

- единичный craft finding → дельта текущего раунда;
- consensus structural gap → изменить brief/prompt/flow/canon и полностью пересобрать;
- повтор в одном run → строка в run-specific generator notes;
- повтор в двух независимых production runs → permanent rule;
- проверяемый повтор → detector/test.

Generator change записывается в `docs/loops/FLOW-CHANGELOG.md` **до** следующего раунда.

## 10. Артефакты run'а

```text
docs/loops/runs/YYYY-MM-DD-name/
  contract.md
  BRIEF.md
  RUBRIC.md
  RUBRIC.sha256
  round-N/
    mechanical.txt
    own-eyes.md
    snapshot.sha256
    screenshots/
    judge-1.json
    judge-2.json
    judge-3.json
    synthesis.md
  RESULT.md
```

Прошлые frozen run'ы immutable. Новый owner rejection создаёт новый run и не переписывает
историю оценки старого результата.
