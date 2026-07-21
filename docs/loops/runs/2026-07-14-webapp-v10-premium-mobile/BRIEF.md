# AiPlus / Kodi Web v10 — premium mobile brief

## Product truth

Ученик 4–7 класса после живого объяснения учителя открывает телефон, видит реальные ошибки, разбирает одну по шагам, затем решает новую задачу без подсказки. AI помогает локализовать сбой, но не выдаёт финальный ответ и не заменяет учителя.

Канонический vertical slice: `Сегодня → ошибка → текущий шаг → feedback → проверочная задача → Сегодня`.

## Register lock

**Регистр:** тёплая интеллектуальная студия — уверенно, живо, дорого, без официоза и без детсадовской геймификации.

Запрещены:

1. dashboard/card soup, bento и одинаковые rounded containers;
2. claymorphism, candy gradients, gummy shadows, цвет как декор на каждом элементе;
3. mascot-head-in-circle, generic cartoon fox, speech-bubble spam;
4. школьная «тетрадь в клетку» как буквальный фон всего экрана;
5. KODI/чужой wordmark вместо реального AiPlus logo;
6. проценты как единственная тема или выдуманная feature — layout обязан выдерживать реальные длинные задачи, формулы и ответы до 15 символов;
7. desktop dashboard, ужатый до 375 px.

## Brand anchors

- Реальный AiPlus logo lockup с оранжевым полем.
- Реальный маскот: tan fox costume, большие уши/глаза, blue sweatshirt, yellow AiPlus emblem.
- Orange — brand event/action, не сплошная заливка интерфейса.
- База: mineral warm-white + deep ink; blue sweatshirt может стать спокойным secondary, но не SaaS primary.

## Experience principles

- На каждом экране один очевидный математический фокус.
- Ученик понимает «где я / что сейчас / что будет после» без чтения onboarding copy.
- Маскот — coach at transitions: встречает, уточняет один шаг, празднует closure. Не комментирует каждую карточку.
- Typography делает 60% атмосферы; character display и спокойный Cyrillic body — разные роли.
- Один signature motif связывает hub, drill и result; он должен работать статически и в motion.
- Premium = точная композиция, material/image quality, authored type, whitespace и micro-interaction; не blur/shadow/gradient quantity.
- Desktop — generous studio adaptation с тем же центром внимания, а не admin panel.

## Shared real scenario for all concepts

- Ученик: Аян, 7 класс.
- Hub: 2 ошибки; ведущая тема «Проценты»; state `revisit`; последняя ошибка `1230`; mastery `0.31` показывать только если это действительно помогает ученику.
- Problem: «Цена товара 1200 ₸ выросла на 15%, а затем снизилась на 10%. Найдите итоговую цену.»
- Active step 1/3: «Сколько тенге составляет рост на 15% от 1200?»
- Input: `180`; feedback: «Верно. Теперь прибавь 180 к исходной цене.»
- Closure: новая задача `800 ₸ +25% −20%`; успешный result возвращает в queue без обещания, что карточка гарантированно исчезнет.

## Required screen/state coverage

- Hub success + loading/error/empty.
- Drill active + wrong/hint + photo unsure + reveal/finished.
- Closure solving + wrong/network + success.
- Mini-srez feedback/final.
- Analytics loading/error/empty/success.
- Login existing/new/error/loading.
- 404.

## Device and accessibility gates

- Primary 375×844, secondary 1280×900.
- No horizontal page overflow; long KaTeX stays local.
- Touch targets ≥44×44, input font ≥16 px.
- Visible keyboard focus; semantic headings/labels.
- `prefers-reduced-motion` preserves meaning and content.
- No offline promise; network failure is explicit with retry.

## Success statement

На 375 px экран воспринимается как настоящий дорогой consumer learning product: первым видна математика, AiPlus узнаётся без чтения, mascot feels intentional, а ни один judge не называет интерфейс MVP, template, dashboard или AI-generated card stack.
