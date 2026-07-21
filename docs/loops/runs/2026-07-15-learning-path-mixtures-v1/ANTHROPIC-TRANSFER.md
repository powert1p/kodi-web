# Claude for Teachers → Kodi: transfer note

Дата исследования: 2026-07-15. Источник зафиксирован на commit
`7c03c83db8223b050b6569ffbe14cd94e229396e` репозитория
[`anthropics/k12-teacher-skills`](https://github.com/anthropics/k12-teacher-skills/tree/7c03c83db8223b050b6569ffbe14cd94e229396e).

## Решение

Claude for Teachers — teacher-authoring product, а не готовый student tutor. В Kodi
переносится педагогический contract и content-quality gate. Американский curriculum,
teacher document workflow и внешние MCP не становятся runtime dependencies.

## Что переносим в learning path v1

1. Для урока явно фиксируются `prerequisite`, target skill, structural cases,
   misconception fingerprints и transfer case.
2. Поддержка ведёт к той же целевой математике, а не заменяет её задачей попроще.
3. Fading внутри маршрута: worked example → до двух supports → один support →
   independent без embedded support → transfer с 0–1 support.
4. Ни одна подсказка не раскрывает ответ и не превращает открытое решение в выбор
   из вариантов или заполнение очевидного пропуска.
5. Final transfer — structurally hardest case и различает основную ошибочную модель.
6. Все student/teacher/runtime artifacts строятся из одного versioned lesson manifest.
7. Student UI не показывает labels `below / at / above`, педагогический жаргон и
   teacher-only данные.

## PC06: misconception fingerprints

- Усредняет проценты без весов по массе растворов.
- Путает массу растворённого вещества и массу всей смеси.
- После добавления воды сохраняет старую общую массу в знаменателе.
- Складывает концентрации вместо масс растворённого вещества.

Transfer-check проходит gate только если условие сохраняет содержательную сложность и
ученик с целевой ошибочной моделью получает отличимый неверный результат.

## Kodi content-quality gate

### Deterministic

- stable identity `content_idx` связывает условие, decomposition и expected answer;
- expected answer отсутствует в pre-submit payload;
- manifest содержит named prerequisite и полный набор structural cases;
- supports монотонно уменьшаются и не превышают `2 → 1 → 0`;
- independent/transfer steps не содержат answer-bearing hints;
- teacher-only поля не сериализуются в student API;
- все численные ответы и единицы пересчитаны сервером;
- финальная задача помечена как hardest/discriminating case.

### Human / LLM judge

- сохраняется cognitive demand целевой темы;
- representation соответствует математической структуре;
- хотя бы одна задача требует объяснения или сравнения стратегии;
- misconception и teacher move специфичны теме, а не boilerplate;
- transfer действительно меняет ситуацию, но проверяет тот же invariant;
- ребёнок понимает приобретённое умение по result screen.

## Готовые open-source patterns для content pipeline

- [`Learning Commons Evaluators`](https://github.com/learning-commons-org/evaluators/tree/fcdf01c006a347e09aee042f986b95cac9f59456):
  адаптировать high-recall candidate matching и строгую проверку alignment
  `problem → learning component`. Coverage считается в обе стороны: какие components
  покрывает задача и какими задачами покрыт каждый component. Runtime SDK и telemetry
  не становятся production dependency; проверка запускается offline при импорте.
- [`Learning Commons Knowledge Graph`](https://github.com/learning-commons-org/knowledge-graph/tree/dcf4549dcdf5ce1dada8b05f04c91068ac58adac):
  взять graph-native schema со stable IDs и progression edges, но наполнить её нашим
  KTP/NIS-графом.
- [`math-olympiad` verifier pattern](https://github.com/anthropics/claude-plugins-official/tree/972e286f4dbc8e0f53f23d870a1e12192faffafc/plugins/math-olympiad):
  solution и decomposition проверяются независимым fresh-context verifier с
  adversarial checks; сомнительные записи quarantined, а не публикуются.

## Не переносим

- CCSS/state standards, IM/OpenSciEd content и американские grade assumptions;
- три статичных tier worksheet как модель детского опыта;
- Claude Learning Mode как свободный student chat;
- DOCX/HTML renderers в first student vertical;
- partner MCP с roster, фото или ответами детей;
- FERPA-позиционирование как замену требованиям Казахстана.

## Лицензия

Корневой репозиторий и две teaching skills опубликованы под Apache-2.0. При прямом
копировании файлов сохраняются LICENSE/NOTICE и отметки об изменениях. В первой
вертикали правила адаптируются как продуктовый contract Kodi; сторонний curriculum
content не импортируется.

## Источники

- [Anthropic: Introducing Claude for Teachers](https://www.anthropic.com/news/claude-for-teachers)
- [Открытый репозиторий teaching skills](https://github.com/anthropics/k12-teacher-skills)
- [Открытые eval rubrics](https://github.com/anthropics/k12-teacher-skills/tree/main/evals)
- [Learning Commons: Scaling Proven Learning Practices](https://learningcommons.org/news/scaling-proven-learning-practices/)
- [Claude for Teachers data and terms](https://support.claude.com/en/articles/15926041-claude-for-teachers-your-data-and-our-terms)
