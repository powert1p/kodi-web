# Benchmark contract — webapp v11

- **Objective:** полностью заново спроектировать визуальный язык и UX React PWA Kodi/AiPlus так, чтобы продукт ощущался дорогим, живым и увлекающим, а математика оставалась главным объектом каждого учебного экрана.
- **Run type:** production redesign, clean slate.
- **Scope:** `/login`, Hub, Drill, Closure, Srez, Analytics, protected 404, global/focus navigation, loading/error/empty/success states, motion and responsive behavior.
- **Behavioral boundary:** API, алгоритмы и продуктовая логика не меняются. Сохраняются существующие маршруты, semantic selectors, мягкая проверка без выдачи ответа, focus-mode и state contracts из `BRIEF.md`.
- **Frozen inputs:** `BRIEF.md`, `RESEARCH.md`, `CONCEPTS.md`, `RUBRIC.md`, `assets/logo-source.jpg`, выбранные PNG-белки из пользовательской Drive-папки и продуктовые документы `docs/VISION.md`/`webapp/AGENTS.md`.
- **Anti-reference:** текущий v10 UI, текущий `webapp/DESIGN_SYSTEM.md`, точный прямоугольный logo lockup, костюм-лиса, тяжёлая luxury-editorial serif-композиция, повторяющийся тёмный stage и любые прежние v7–v10 макеты.
- **Brand-source rule:** исходный логотип задаёт только происхождение бренда, характер wordmark и дисциплину оранжевого. В продукте нельзя вставлять lockup один-в-один; новый code-native знак должен быть самостоятельной адаптацией.
- **Mascot rule:** использовать только иллюстрированных белок из пользовательской Drive-папки. Белка поддерживает контекст и эмоцию, но не конкурирует с математикой и не превращается в постоянный avatar/bubble.
- **Shared register:** `увлечённый`.
- **Forbidden defaults:** card soup; app-store landing page; claymorphism; candy palette; SaaS blue; огромная serif-типографика; orange wall/полноэкранная оранжевая заливка; mascot-first hero; декоративные формулы; generic AI gradients; bento; glassmorphism.
- **Divergence gate:** до production-кода сравниваются три пространственно разные концепции на одинаковом Hub/Drill/Srez контенте, 375×844 и 1280×900. Token swap не считается новой концепцией.
- **Concept selection:** собственная визуальная проверка + минимум два независимых screenshot-reviewer; решение принимается по frozen rubric, а не по описанию концепции.
- **Production selection:** три независимых judge на immutable renders и кодовых evidence; исправляются consensus deltas, а слабое macro-направление отбрасывается вместо декоративного patch stacking.
- **Mechanical gate:** lint, design lint, typecheck, tests, production build; browser matrix 375/1280; console/network/overflow; keyboard focus; touch targets; reduced motion; loading/error/empty/success.
- **Terminal condition:** все mechanical gates green и READY threshold из `RUBRIC.md` выполнен.
- **Stop policy:** без произвольного числа раундов. Каждый раунд заканчивается immutable renders, scorecard и конкретными deltas.

