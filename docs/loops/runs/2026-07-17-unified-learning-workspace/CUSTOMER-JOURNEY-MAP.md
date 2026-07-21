# Customer Journey Map — от регистрации до первого подтверждённого навыка

## North star

Новый ученик регистрируется, понимает логику подготовки, начинает конкретную тему и проходит
полный цикл `самостоятельная попытка → AI feedback → помощь при необходимости → transfer`, не
теряя задачу и не гадая, куда нажать дальше.

| Момент | Цель ребёнка | Видимая поверхность | Мысль/риск | Поведение системы | Recovery и acceptance evidence |
|---|---|---|---|---|---|
| 1. Регистрация | Войти и понять, что будет дальше | Короткая последовательная форма | «Меня сразу заставят решать?» | Обещает: сначала настройка и короткая диагностика, потом личный маршрут | Draft сохраняется; ошибки у поля; нет скрытого старта задачи |
| 2. Согласие и адаптация | Настроить темп без экзаменационного давления | Один вопрос за шаг | «Зачем вам фото?» | До upload объясняет обработку и получает consent взрослого | Без consent фото не отправляется; можно продолжить setup позже |
| 3. Диагностика | Показать текущий уровень | Фокус на одном вопросе | «Это оценка?» | Объясняет, что ответы выбирают стартовые темы | Ответ и progress сохраняются; refresh возвращает текущий вопрос |
| 4. Маршрут | Понять, с чего начинать и почему | Первый topic + короткая причина | «Почему именно это?» | Показывает один recommended start и ближайшие темы как контекст | Один CTA `Начать тему`; нет каталога всех функций |
| 5. Handoff в урок | Понять цель темы | Короткий intro перед stable workspace | «Что я должен уметь после?» | Формулирует observable topic goal и формат доказательства | `Начать задачу` переводит в workspace; дальше shell не меняется |
| 6. Independent task | Решить самому | Task anchor + response dock | «Что отправлять?» | Условие и instruction видимы; photo — default, typed — alternative | Выбранное фото/typed draft локально и серверно привязаны к task |
| 7A. Фото | Передать полный ход | Photo selection внутри dock | «Видно ли всё?» | Показывает preview/name и checklist без backend semantic reject | До submit можно заменить; после submit draft не теряется |
| 7B. Typed answer | Быстро проверить мысль | Inline answer composer | «Можно без фото?» | AI даёт formative verdict; UI честно говорит, что mastery требует самостоятельного решения | Можно вернуться к photo без потери typed attempt |
| 8. Проверка | Дождаться результата | Task остаётся, contextual layer показывает progress | «Приложение зависло?» | Durable processing, понятный status, safe retry с тем же idempotency key | Refresh/resume возвращает processing или сохранённый verdict |
| 9A. Correct | Понять, что доказано | Compact feedback рядом с task | «Что дальше?» | Называет подтверждённые шаги и открывает следующую задачу | Один CTA; mastery обновляется только от independent photo evidence |
| 9B. Needs revision | Исправить конкретное место | Локализованный feedback | «Где именно ошибка?» | AI указывает шаг, evidence и предлагает retry/help | Task/attempt остаются; неверный ответ не превращается в длинную лекцию |
| 9C. Uncertain/recovery | Дать AI читаемый input | Local recovery | «Меня посчитали неправым?» | Явно говорит, что математический verdict не вынесен | `Переснять`, `Ввести фрагмент`, `Повторить`; ошибка mastery не записана |
| 10. Просьба о помощи | Сдвинуться с места | Hint/tutor layer поверх workspace | «Только не говори ответ сразу» | Первый ход — вопрос/ориентир по текущему task/step | Task всегда видима; thread и rung сохраняются |
| 11. Guided step | Выполнить ближайший шаг | Тот же task anchor + compact step composer | «Это всё ещё та же задача?» | Показывает mode `Разбор`, принимает text/options, даёт AI feedback | Нет фото каждого шага; activity не повышает mastery |
| 12. Transfer | Проверить самостоятельность | Workspace меняет task content, но не geometry | «Теперь я смогу сам?» | Даёт новую задачу той же skill family, помощь скрыта до intent | Только самостоятельное полное фото создаёт mastery evidence |
| 13. Topic result | Увидеть реальный результат | Evidence summary | «Что именно стало лучше?» | Показывает подтверждённый навык и следующий recommended topic | Не выдаёт fake points; можно закончить и безопасно продолжить позже |

## Emotional curve

`неуверенность → ориентация → самостоятельная концентрация → безопасная проверка → конкретное
исправление → подтверждённая способность`.

Критическая UX-точка — переходы 8–12. В них запрещено менять страницу: именно там ребёнок
сопоставляет feedback со своей работой и решает, нужна ли помощь.

## Measurable journey signals for the implementation Goal

- `time_to_first_meaningful_action` после lesson start;
- доля attempts с потерей draft/reload = 0;
- typed→photo и hint→transfer completion;
- `uncertain` recovery success без записи wrong mastery;
- hint rung distribution и быстрые прокликивания;
- assistant turns, привязанные к task/step, без answer leakage;
- return-to-same-state после refresh/relogin;
- child usability: 5-second orientation, task recall after feedback, next-action success.

