# Research — AI-native premium mobile design

Дата: 2026-07-14. Цель: не найти «ещё один красивый prompt», а собрать воспроизводимый процесс, который не возвращается к rejected design system и не заканчивается generic AI UI.

## Что подтвердили источники

1. **Первый AI draft почти неизбежно усреднён.** Figma прямо пишет: без реальных компонентов, контента, ограничений и edge cases убедительный первый экран остаётся чужим и требует переписывания. Следствие для Kodi: до визуальной генерации фиксируются реальные строки, состояния, длины формул и педагогические запреты.
   - https://www.figma.com/blog/introducing-make-kits-and-make-attachments/
   - https://www.figma.com/blog/what-is-good-design-in-the-age-of-ai/
2. **Контекст надо передавать исходниками, а не монстр-промптом.** Brand assets, screenshots, data, product spec и state matrix остаются отдельными material inputs. Design guidelines — короткие, imperative и task-specific.
   - https://help.figma.com/hc/en-us/articles/33665861260823-Add-guidelines-to-Figma-Make
   - https://developers.figma.com/docs/code/write-design-system-guidelines/
3. **Нужны несколько layout directions и версии.** Claude Design и Figma Make рекомендуют 2–3 альтернативных layout, сохранение версий и затем точечные комментарии. Broad prompt меняет структуру; point edit меняет деталь.
   - https://support.claude.com/en/articles/14604416-get-started-with-claude-design
   - https://www.figma.com/blog/introducing-figma-make/
4. **Mobile-first должен быть задан как момент использования, а не как breakpoint.** Vercel показывает, что «works on mobile» даёт сжатый desktop, а audience + context + device + constraint дают настоящий mobile-first. Structural prompts и visual tweaks должны быть разнесены.
   - https://vercel.com/blog/how-to-prompt-v0
5. **Прототипирование должно оставаться в среде реального поведения.** Код/интерактивность и реальные состояния проверяются раньше, чем UI превращается в систему компонентов.
   - https://vercel.com/blog/working-with-figma-and-custom-design-systems-in-v0
   - https://www.figma.com/solutions/ai-design-systems-generator/
6. **Базовая mobile craft — не вкусовщина.** Основной контент помещается без горизонтального scroll, controls ≥44 pt, controls находятся рядом с тем, что меняют, изображения не искажаются.
   - https://developer.apple.com/design/tips/

## Что реально сработало у владельца

Источник — Claude session `caf0c82e-6ef0-490b-9b8d-9d437d884cf5` и локальный `/Users/esetseitkamal/Documents/design-lab/FLOW.md` v3.

- Для QARA builder получил прямой запрет читать старый `DESIGN.md`: направление задавалось clean-slate brief.
- `ui-ux-pro-max` использовался как reference library, не как арт-директор.
- `REGISTER LOCK` фиксировал характер и 2–3 запрещённых AI-defaults.
- Builder сам смотрел реальные 1280/375 renders и середину scroll, а не сдавал первый code pass.
- Три независимых judges возвращали численные scores и конкретные deltas.
- После первого `7.25` исправили не цвета, а макро-композицию: full-bleed contrast moment, grid breaks, type/image collision, честную signature и полноценную mobile form.

Почему promise «дальше всегда красиво» не сработал: legacy automation объявляла любую project DS законом и повторно инжектила старый визуальный канон. Значит, для full redesign старая DS может быть только behavioral evidence и anti-reference.

## Новый рабочий flow для Kodi

1. **Truth packet:** audience, real journey, real copy, data lengths, state matrix, logo/mascot, technical constraints.
2. **Register lock:** характер продукта + запрещённые defaults.
3. **Divergence:** минимум три spatial systems на одном и том же контенте. Не «три палитры».
4. **Render before system:** 375/1280 screenshots и interaction slice до изменения production DS.
5. **Frozen judging:** независимые judges оценивают одинаковые артефакты по одной rubric; direction выбирается по evidence, не по самоописанию.
6. **Design kernel:** только победитель превращается в tokens, type, spacing, imagery, mascot protocol, motion и component rules.
7. **Vertical slice first:** Hub → drill → feedback/closure на реальном поведении.
8. **Point-delta loop:** каждый раунд чинит максимум несколько consensus deltas; плохой macro-direction выбрасывается, а не полируется.
9. **State and device gate:** loading/error/empty/success, keyboard, touch, reduced motion, console, overflow, 375/1280.
10. **Ship gate:** tests/lint/typecheck/build + минимум два независимых reviewers + frozen rubric threshold.

## Вывод для текущего редизайна

`ui-ux-pro-max` по общему запросу предложил claymorphism, синий primary, оранжевый CTA и bubbly cards — ровно класс уже rejected решений. Поэтому его output зафиксирован как предупреждение: catalogue search помогает проверять accessibility/patterns, но direction выбирают product truth, clean-slate concepts и screenshot judgement.
