# Frozen product/UX rubric — learning path v1

Каждый judge получает одинаковый brief и immutable screenshots трёх концепций на 375×844 и 1280×900. Label концепции скрыт. Описание не компенсирует то, чего не видно на экране.

## Оси 0–10

| Ось | 9–10 | 5–7 = провал |
|---|---|---|
| **time_to_first_value** | За ≤10 секунд и ≤2 taps понятно, какой урок и зачем начать | Нужно сканировать очередь, меню или выбирать режим |
| **cognitive_focus** | Один математический объект и одно следующее действие командуют viewport | Параллельные cards, mascot, chrome или помощь спорят с задачей |
| **pedagogical_sequence** | Worked → guided fading → independent → transfer считывается и поддерживает размышление | Набор несвязанных задач или готовое решение вместо обучения |
| **task_quality** | Содержательная многошаговая математика с понятной целью и честным evidence | Примитивная арифметика, случайный warm-up или фальшивый прогресс |
| **progress_legibility** | Ясно, где ребёнок в учебном пути, текущем блоке и внутри урока | Дневная очередь, проценты/очки без смысла или перегруженная карта |
| **assistance_disclosure** | Поддержка появляется только после попытки и относится к текущему шагу | Чат/фото/теория/подсказки конкурируют до начала работы |
| **state_integrity** | Resume, wrong, retry, result и completion не теряют ввод/прогресс | Happy-path mockup, непонятное восстановление или ложное завершение |
| **premium_coherence** | Accepted AiPlus v11 language выглядит как законченный учебный продукт | MVP, dashboard template, candy game или декоративная брошюра |

## Concept gate

- Три пространственно разные концепции, 375×844 и 1280×900.
- Минимум два blind reviewer.
- Победитель: каждая ось ≥8.0, среднее ≥8.5; `time_to_first_value`, `cognitive_focus`, `pedagogical_sequence`, `task_quality` ≥8.5.
- Нет consensus high delta. Если ни один вариант не проходит, пересобирается macro-direction.

## Production READY

- Backend/frontend mechanical gates green.
- Корневой экран считывается как накопительный curriculum path, а не как дневное закрытие ошибок.
- Реальные API и persistence, без mock-only happy path.
- Каждая ось у каждого production judge ≥8.0, среднее панели ≥8.5.
- Ключевые четыре оси ≥8.5 у каждого judge.
- Минимум 2/3 judges подтверждают, что это рабочий продукт, а не MVP-demo.
- Нет consensus high delta.

## Judge JSON

```json
{
  "scores": {
    "time_to_first_value": 0,
    "cognitive_focus": 0,
    "pedagogical_sequence": 0,
    "task_quality": 0,
    "progress_legibility": 0,
    "assistance_disclosure": 0,
    "state_integrity": 0,
    "premium_coherence": 0
  },
  "avg": 0,
  "working_product": false,
  "evidence": [],
  "top_deltas": [],
  "verdict": "READY | NOT_YET"
}
```
