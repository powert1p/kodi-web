# webapp — UI instructions

- Это действующий React 19 PWA продукта на `/app/`. `frontend/` — legacy Flutter и не является
  источником решений для этой директории.
- До UI-работы читать `../docs/VISION.md`, `../docs/loops/DESIGN-FLOW.md` и active run/brief,
  указанный в task или contract; не выбирать run только по дате. `DESIGN_SYSTEM.md` — канон для maintenance; при явном redesign или
  rejection текущего вида это anti-reference до победившего frozen concept.
- Токены менять только в `src/theme/tokens.css`/`fonts.css`; компоненты не получают сырые hex/px.
- Существенный UI проверять на 375×844 и 1280×900: console, overflow, keyboard, touch,
  loading/error/empty/success и reduced motion.
- До «готово»: `npm run lint`, `npm run lint:design`, `npx tsc -b`, `npx vitest run`, `npm run build`.
- Для значимого redesign нужны три spatial/art direction до production, generator-level loop и
  blind reviewers по `../docs/loops/rubric-design.md`; ниже frozen bar результат не `READY`.
