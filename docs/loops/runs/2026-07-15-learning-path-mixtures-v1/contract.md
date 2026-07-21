# Benchmark contract — learning path v1

- **Objective:** превратить mobile PWA из очереди разрозненных ошибок в рабочий учебный продукт, где ребёнок сразу получает один понятный урок и заканчивает его доказуемым результатом.
- **First vertical:** тема `PC06` «Смеси и концентрации», три урока от сохранения массы вещества до задач с неизвестным количеством смеси.
- **Scope:** стабильная связь `Problem ↔ decomposition`, server-graded и persistent learning session, экран «Мой путь» с текущим curriculum block, focus-flow урока, результат урока, loading/error/resume/wrong/help/completed states.
- **Non-goals:** полный контент всех 13 блоков, новый placement-test, OCR/voice/live-canvas внутри урока, переписывание существующих drill/srez, production deploy.
- **Visual boundary:** принятая v11 design system остаётся визуальным каноном. Текущий Hub и его информационная архитектура — anti-reference. Новый flow обязан быть структурно новым, а не перестановкой карточек.
- **Learning boundary:** worked example → guided completion с пропусками → две independent задачи → transfer. Mastery/BKT меняется только по independent/transfer evidence, но не по показанному примеру и не по guided ответу.
- **Security boundary:** ожидаемый ответ и внутренние правила grading не попадают в pre-submit API; проверка выполняется сервером.
- **Identity boundary:** декомпозиция выбирается только по стабильному content identity. Неоднозначная или повреждённая связь закрывается ошибкой/карантином, а не подменяется «похожей» задачей.
- **Shared register:** `собранный`.
- **Forbidden defaults:** дневная очередь «Сегодня» как главная модель, dashboard/card soup, параллельные CTA, выбор между «чат/фото/теория/подсказка» до ошибки, случайная разминка, детская геймификация вместо результата, mascot-first hero, прогресс без названного умения.
- **Divergence gate:** до production-кода сравниваются три пространственно разные концепции на одинаковом контенте, 375×844 и 1280×900. Перекраска одной сетки не считается концепцией.
- **Concept selection:** frozen rubric + минимум два blind screenshot-reviewer. Побеждает лучший minimum score, а не описание идеи.
- **Mechanical gate:** backend tests, frontend lint/typecheck/tests/build, real browser 375/1280, console/network/overflow, keyboard focus, touch targets, reduced motion, loading/error/new/resume/wrong/result states.
- **Terminal condition:** рабочий vertical slice проходит механические проверки и production READY threshold из `RUBRIC.md`; следующий backlog зафиксирован отдельно.
