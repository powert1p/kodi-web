# Round 0 — rendered concept decision

## Решение

Победитель: **A «Пульс решения»**, 3 голоса из 3. Это направление, а не готовый
шаблон: все судьи дали `NOT_YET`, поэтому `prototype.html` нельзя переносить буквально.

Средние оценки A: typography 7.67, color 7.67, composition 7.00, motion 4.00,
signature 5.67, craft 7.00, brief fit 7.00, punch 7.67. Общий средний балл 6.71.

## Почему A

- Лучший баланс визуального удара, ясной иерархии и читаемого учебного текста.
- Hub, drill и srez сохраняют primary job на 375 и 1280 px.
- Нет блокирующего clipping B и разрушительной condensed-типографики C.
- Cobalt-сцена и trace ближе всего к продуктовой идее «мысль становится видимой».

## Обязательные изменения до React

1. `ProofTrace` получает реальные данные: количество ошибок на hub, текущий шаг drill,
   позицию вопроса srez. Декоративных узлов нет.
2. Spatial model экранов проектируется отдельно; общий prototype DOM не переносится.
3. Tektur используется только для коротких display anchors. Условия, инструкции и длинные
   заголовки остаются в Onest/Golos.
4. Volt — фокус и действие, не постоянный acid fill. Рабочая поверхность drill — спокойная bone.
5. Locked/checking/retry/completed имеют читаемый текст и проходят AA без opacity на контейнере.
6. Trace появляется один раз, фиксирует break point и меняет active node. Бесконечного dash-loop нет.
7. Mobile navigation не перекрывает content/signature; focus flows не показывают global nav.

Эти deltas зафиксированы в `DESIGN-V8.md` и входят в следующий benchmark.
