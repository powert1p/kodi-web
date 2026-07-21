# Frozen rubric — Codex design-flow adaptation

Каждый пункт бинарный. Порог READY: **12/12**, зелёные mechanical checks и минимум два
независимых verdict `READY` без блокирующей дельты.

1. **Routing:** ясная UI-правка идёт коротким pipeline; редизайн, отвергнутый текущий вид,
   неизвестное направление или явный запрос «до планки» идут generator-loop; две неудачи
   pipeline эскалируют в generator-loop.
2. **Hard creative bar:** результат ниже frozen creative bar никогда не называется готовым;
   budget/plateau ниже планки дают `NOT_READY` или `UNCERTAIN`.
3. **Generator first:** повторяющийся consensus-дефект меняет входы генератора/flow/canon до
   следующего раунда, а не только локальный CSS артефакта.
4. **Codex roles:** текущий Codex — maker/integrator; external Codex и Claude/Opus workers не
   требуются; native subagents используются для bounded read-only review/test work.
5. **Clean slate:** при явном редизайне текущие design system, компоненты и screenshots —
   behavior evidence и anti-reference, не визуальный канон.
6. **Concept divergence:** до production-кода сравниваются минимум три направления с разными
   spatial model, typography, atmosphere и signature; token-reskin старого DOM не считается.
7. **Product adaptation:** flow рассчитан на mobile learning product: математика и действие
   остаются фокусом, signature живёт в реальных состояниях продукта, а не зависит от
   лендингового scroll spectacle.
8. **Assets and type:** raster генерируется через доступный Codex `imagegen`, визуально
   проверяется; шрифты подтверждают Cyrillic и казахские glyphs; placeholders/stock не проходят.
9. **Evidence gate:** mechanical checks, реальные 375/1280 renders, console/overflow/focus/
   reduced-motion/states и собственный визуальный осмотр предшествуют judging.
10. **Blind judges:** минимум два независимых judge получают один frozen snapshot и rubric,
    без предыдущих оценок; maker не judge; raw verdicts сохраняются.
11. **Delta comparison:** со второго раунда кандидат blind-сравнивается с best-so-far;
    повторная полировка без измеримого выигрыша не продолжает цикл.
12. **Project wiring:** `webapp/AGENTS.md`, `docs/loops/DESIGN-FLOW.md`, design rubric и
    generator changelog согласованы, ссылки разрешаются, прошлые frozen run'ы не изменены.
