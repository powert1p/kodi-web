# Kodi Error Trainer — Design System (v2, claymorphism-light)

> Replaces the rejected dark "brain-gym" attempt. Evidence-based via ui-ux-pro-max: claymorphism is the documented best-fit style for children's math-education apps. Direction: **bold + energetic but friendly and tactile** — light, candy-colored, soft-3D, springy. NOT dark, NOT edgy, NOT generic.

## Style — Claymorphism (light)
- Soft inflated 3D "toy" surfaces. Big rounded radii. Multi-layer soft shadows (outer drop + inner highlight), never hard lines.
- Tactile micro-interactions: press = spring squish `scale(0.94)` with bounce `cubic-bezier(0.34, 1.56, 0.64, 1)`, ~180–220ms. Restore on release. Cards/buttons feel pressable.
- Background never pure white: soft tinted base + slow-drifting decorative blobs (respect `prefers-reduced-motion`).
- Energetic via vibrant candy color + chunky shapes + springy motion — NOT via darkness.

## Color tokens (CSS variables) — "Kids Learning (Math)" palette
```
--bg:            #EFF6FF   /* soft light-blue base (never pure white) */
--surface:       #FFFFFF   /* clay cards */
--surface-muted: #F1F5FD
--text:          #0F172A   /* primary (AA on white/light) */
--text-muted:    #64748B
--border:        #E4ECFC
--primary:       #2563EB   /* learning blue — primary actions, focus ring */
--on-primary:    #FFFFFF
--secondary:     #F59E0B   /* play amber — rewards, accents */
--accent:        #EC4899   /* fun pink — sparingly, highlights */
--success:       #16A34A   /* progress green (AA) */
--warning:       #F59E0B
--danger:        #DC2626   /* use rarely; mistakes are NOT framed as red errors */
```
Mistake states (growth-mindset, supportive — never harsh red):
```
--state-revisit: #6366F1 (indigo, "разберём")   --state-almost: #F59E0B (amber, "почти")   --state-got: #16A34A (green, "готово")
```
Radii: `--r-card: 28px`, `--r-tile: 24px`, `--r-button: 18px`, `--r-pill: 999px`.
Clay shadow (light): `box-shadow: 10px 12px 24px rgba(37,99,235,.12), -6px -6px 16px rgba(255,255,255,.9), inset 0 1px 0 rgba(255,255,255,.6);`

## Typography — rounded + FULL CYRILLIC (ru/kz), self-hosted for offline
- Display / headings / big numerals: **M PLUS Rounded 1c** 700/800/900 (cyrillic + cyrillic-ext, chunky rounded clay feel).
- Body / labels / buttons: **Nunito** 400/600/700/800 (cyrillic, highly readable, rounded).
- NEVER Inter / Roboto / Arial. Inputs ≥16px (no iOS zoom). Tabular numerals for scores/counters.
- Math: KaTeX, `throwOnError:false`, `overflow-x:auto` on a WRAPPER div (not `.katex`).

## Motion
- Animate only `transform` / `opacity`. Staggered list reveal 30–50ms/item, 180–260ms each, ease-out enter.
- Press squish (above). Celebrations use spring/confetti on closure. Wrap all non-essential motion in `@media (prefers-reduced-motion: reduce)`.

## Information architecture (this product)
- Bottom nav ≤3, label+icon, active highlighted: **Срез** (hub) · **Прогресс** (analytics) · (later: Профиль).
- **Hub:** warm greeting + a "today's срез" hero summary (count + supportive line + progress ring), then claymorphic error TILES grouped/ordered by priority — each tile shows topic, the math (KaTeX), a friendly supportive state (mood chip/мини-маскот, not a red badge), tap → drill. States: loading (clay skeletons), empty (celebratory "Всё разобрано 🎉" + go-practice), error (retry).
- **Drill (headline):** big friendly problem card; level intro (1 «разберём тему» / 2 «вспомним» / 3 «почти — проверим где»); vertical step **ladder** with "шаг 2 из 4" progress; hint reveal (never the answer); big tactile **«Сфотографировать решение»** button → diagnosis card with the located step highlighted + collapsible transcription ("что я увидел" — receipts) + supportive cause. Reveal worked step only as last resort.
- **Closure:** celebratory reward (spring/confetti), verification problem solved hint-free → "ошибка закрыта".
- **Analytics:** friendly "твои частые ошибки" with playful bars.

## Accessibility / mobile (must)
- Contrast ≥4.5:1 text (clay pastels are low-contrast — verify each pair). Touch targets ≥44px, 8px gaps. `viewport-fit=cover`, safe-area insets, `min-h-dvh`. Focus rings visible (use --primary). Color never the only signal (icon/text + color). Dynamic Type / reduced-motion safe.

## Tone (growth-mindset)
Mistake = «где растёт мозг». Praise effort, not ability. No angry red "НЕПРАВИЛЬНО". Encouraging, warm, a little playful — smart, not babyish (NIS students).
