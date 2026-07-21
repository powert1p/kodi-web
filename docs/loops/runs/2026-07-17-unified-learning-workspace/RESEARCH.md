# Research → применимые UX-критерии

Исследование задаёт criteria и ограничения, но не подменяет child usability test.

## Primary sources

1. [Nielsen Norman Group — Ten Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/):
   visibility of system status, match with the real world, user control, consistency, error
   prevention/recovery. Перевод в DoD: processing видим, task не исчезает, back/retry не теряют
   draft, error находится рядом с причиной.
2. [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/): focus appearance/not obscured, error
   identification/suggestion, target size and non-drag alternatives. В продукте принят более
   строгий child/mobile target 44×44 px при WCAG AA minimum как floor.
3. [OpenAI Study Mode](https://help.openai.com/en/articles/11780217-chatgpt-study-mode-faq):
   Socratic questions, context use and explicit acknowledgement that AI may make mistakes.
   Перевод: tutor начинает с одного grounded question, uncertainty имеет отдельный state.
4. [Anthropic — Claude for Education](https://www.anthropic.com/news/introducing-claude-for-education):
   guided learning через questions/reasoning вместо прямой выдачи ответа. Это product source,
   не доказательство learning gain.
5. [Roll, Aleven, McLaren & Koedinger, 2011](https://pact.cs.cmu.edu/pubs/Roll%2C%20Aleven%2C%20McLaren%20%26%20Koedinger%202011.pdf):
   contextual progressive hints и metacognitive feedback on help-seeking. Переносится принцип
   ladder и защита от help abuse; число rung для Kodi остаётся гипотезой.
6. [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/): documented
   roles, monitoring, uncertainty and risk treatment. Перевод: AI/backend/UI responsibility
   разделены, raw/normalized response логируются, uncertainty не маскируется.

## Frozen criteria derived for this run

- system status видим без исчезновения problem context;
- error/feedback локальны и всегда содержат следующий recoverable action;
- one primary action, photo default + typed alternative;
- contextual Socratic help, progressive ladder, explicit full-solution reveal;
- `correct / needs_revision / uncertain`, а не forced binary verdict;
- resume preserves task, draft, verdict, hint rung and tutor thread;
- keyboard/touch/focus/overflow and Russian/Cyrillic glyph proof;
- no claim that four hints, a static concept or an AI product source proves learning growth.

## Negative findings

- Нет первичного исследования, доказывающего оптимально ровно четыре hint level для детей 10–13.
- Product pages OpenAI/Anthropic/Khan-style tutors не являются RCT Kodi photo-flow.
- WCAG minimum target не является оптимальным детским mobile size, поэтому Kodi использует 44 px.
- Static render не доказывает, что реальный ребёнок поймёт flow; нужен moderated usability test.

