# Frozen design rubric — adaptive photo-first NIS

Оценка по восьми осям 0–10. Для production READY каждая ось каждого judge должна быть не ниже
8.0, среднее каждого judge — не ниже 8.5, `math_focus` и `premium_distinctiveness` — не ниже
8.5. Минимум два из трёх production judges должны дать `wow=true`; все три — `READY`.

## Оси

1. `product_truth` — последовательность adaptation → diagnostic → result → route → explicit
   start → photo-first → explicit guided → transfer не искажена и не замаскирована UI.
2. `next_action_clarity` — ребёнок 10–13 лет за пять секунд понимает этап, причину и одно
   следующее действие; функции не конкурируют между собой.
3. `math_focus` — задача, условие и собственное решение визуально важнее branding, mascot,
   progress, подсказок и decorative motion.
4. `composition_responsive` — mobile и desktop имеют намеренную композицию; нет card soup,
   растянутого phone layout, page-level overflow или провала первого viewport.
5. `typography_craft` — реальная кириллица/казахские glyphs, учебный текст ≥18 px, читаемая
   математика, устойчивый rhythm, точные states и touch targets ≥44 px.
6. `premium_distinctiveness` — art direction ощущается дорогой и собственной, но не взрослой
   luxury/official и не копией Duolingo; orange дисциплинирован.
7. `signature_evidence` — одна code-native signature проходит через route/task/result и
   визуализирует только реальные server evidence, а не fake progress.
8. `interaction_accessibility` — focus, keyboard order, accessible names, aria-live, local
   recoverable errors, preserved input, non-color status и reduced-motion semantics.

## Critical detector flags

Любой flag блокирует READY вне зависимости от среднего:

- регистрация снова ведёт прямо в урок;
- onboarding или diagnostic невозможно возобновить;
- guided запускается без явного действия ребёнка;
- guided или подсказанный ответ засчитывается как mastery;
- photo-first требует фото каждого шага;
- unreadable/uncertain photo превращается в «неверно»;
- внутренний id, fake score/duration/progress или несохранённый ввод показан пользователю;
- mascot/illustration перекрывает условие или primary action;
- второй primary CTA, math text <18 px, touch target <44 px, page overflow;
- успешный mock/fallback выдан за реальный Gemini verdict;
- console/request error на happy path или недоступен recovery path.

## Concept round

Два независимых reviewer получают только immutable screenshots и этот rubric. Concept round не
объявляет production READY; он выбирает пространственную систему без critical flags и с лучшими
`next_action_clarity`, `math_focus`, `composition_responsive`, `premium_distinctiveness` и
`signature_evidence`.

## Production round

Три независимых judge получают полный state matrix на 375×844 и 1280×900, frozen contract,
mechanical results и этот rubric. Mixed/absent verdict означает `NOT_YET` или `BLOCKED`.
