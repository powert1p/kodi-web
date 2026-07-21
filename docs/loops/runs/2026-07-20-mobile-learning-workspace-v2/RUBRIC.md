# Frozen rubric — mobile learning workspace v2

Каждая ось оценивается `0..10` по production render и interactive journey. `8` означает
production-worthy без крупного долга; `9` — заметно сильный и product-specific результат;
`10` — исключительный результат без содержательного улучшения в scope.

## Axes

1. **first_action_clarity** — за 3 секунды понятны задача, режим и одно следующее действие.
2. **journey_continuity** — условие, ответ, feedback и tutor не рвутся между страницами; return
   восстанавливает task, draft, scroll и focus.
3. **math_focus** — математика визуально сильнее бренда, прогресса, AI chrome и decoration.
4. **guided_instruction** — каждый шаг явно говорит, что сейчас записать и в каком формате;
   feedback локален, честен и не выдаёт ответ.
5. **tutor_usefulness** — AI отвечает на реальный вопрос ребёнка, различает вопрос/«не знаю»/
   проверку мысли, даёт минимальную помощь и сохраняет learner agency.
6. **mobile_comfort** — mobile-first reading order, keyboard-safe composer, targets ≥44 px,
   удобная плотность, отсутствие fixed-dock trap и horizontal overflow.
7. **accessibility_resilience** — семантика, labels, keyboard, focus trap/restore, contrast,
   reduced motion, loading/error/empty/success states и Cyrillic/math glyphs работают.
8. **premium_distinctiveness** — зрелая Kodi-specific editorial система с дисциплинированным
   orange accent; не MVP, не шаблон AI/dashboard, не token-reskin старого DOM.

## Frozen threshold

- каждая ось `≥8.0`;
- среднее `≥8.5`;
- `first_action_clarity`, `journey_continuity`, `math_focus`, `mobile_comfort` `≥8.5`;
- critical flags = 0;
- каждый из трёх blind judges возвращает `READY`; mixed/missing verdict — не READY;
- open P0/P1 = 0.

## Critical flags and caps

- semantic verdict вынесен скриптом, correct typed требует фото, guided увеличивает mastery или
  AI раскрывает protected answer → critical; relevant pedagogy axis `≤4`.
- ребёнок не может понять ожидаемое действие шага без догадки → `guided_instruction ≤5`.
- tutor выдаёт только canned «следующий шаг» либо игнорирует вопрос → `tutor_usefulness ≤5`.
- route/page change, lost draft/scroll/focus или task anchor исчезает при feedback/tutor →
  `journey_continuity ≤4`, critical.
- target <44 px, obscured input/focus, overflow >1 px, console error или keyboard закрывает CTA →
  `mobile_comfort ≤4`, critical.
- более одного конкурирующего primary CTA в current action, giant component занимает viewport без
  учебной причины или desktop DOM просто сжат media-query → соответствующая UX axis `≤5`.
- token/radius reskin старого трёхзонного DOM, generic card soup, copied mascot/logo or fake
  progress → `premium_distinctiveness ≤4`.

## Judge response

```json
{
  "judge": "blind-id",
  "scores": {
    "first_action_clarity": 0,
    "journey_continuity": 0,
    "math_focus": 0,
    "guided_instruction": 0,
    "tutor_usefulness": 0,
    "mobile_comfort": 0,
    "accessibility_resilience": 0,
    "premium_distinctiveness": 0
  },
  "average": 0,
  "critical_flags": [],
  "p0_p1": [],
  "evidence": [],
  "confidence": 0,
  "verdict": "READY|NOT_YET|UNCERTAIN"
}
```

