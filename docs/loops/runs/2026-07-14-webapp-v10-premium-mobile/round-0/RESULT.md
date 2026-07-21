# Round 0 — concept selection

Verdict: **NOT_YET**. Это отбор направления, не production acceptance.

| Reviewer | Equality | Atelier | CUT | Choice |
|---|---:|---:|---:|---|
| Product | 7.61 | 7.53 | 7.03 | Equality |
| Aesthetic | 7.68 | 7.24 | 7.08 | Equality |
| Craft | 7.51 | 7.78 | 7.43 | Atelier |

Mechanical baseline у 18 concept renders зелёный: console clean, fonts/images
loaded, no horizontal page overflow, controls ≥44 px, input text ≥16 px.

## Consensus deltas

1. Сохранить Equality bracket/slot, но убрать collision proof chain с mascot.
2. Использовать whitespace, Literata/Onest и спокойный rhythm Atelier.
3. Заменить vertical desktop headline на понятный queue rail.
4. Реализовать состояния active/wrong/hint/photo unsure/network/reveal/finished и
   Hub loading/error/empty/success.
5. Сделать signature transition: введённое значение входит в slot и фиксируется в
   равенстве; reduced motion получает мгновенный эквивалент.
6. Выделить long-math viewport с локальным scroll/wrap и проверить реальные длинные
   данные на 320/375/1280.
7. Оставить mascot только в intentional transition moments; подготовить отдельные
   mobile/desktop crops и ленивую загрузку.

