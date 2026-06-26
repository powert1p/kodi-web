# Kodi Error Trainer — Design System (v3, Duolingo-style / warm orange)

> Owner direction: **Duolingo-style, warm orange (NOT bright/neon)**. Friendly, gamified, encouraging, mascot-led. Clean light/cream surfaces; depth lives in chunky 3D push-buttons, not heavy clay shadows. Growth-mindset tone. (Supersedes v2 claymorphism.)

## Style — "Duolingo-ish" gamified education
- Clean, light, generous whitespace. ONE dominant brand color = **warm orange**. Cards are fairly FLAT (thin subtle border + tiny shadow), NOT soft-blurry clay.
- **Signature = chunky 3D push-button** (the most important element): rounded, solid fill, a SOLID darker bottom edge via `box-shadow: 0 4px 0 var(--edge)` (no blur). On press: `translateY(4px)` + shrink the edge to `0 0 0` — the satisfying "mechanical press". Use for every primary CTA, answer options, big actions. ~56px tall, bold uppercase-ish label.
- Rounded everything (cards ~16–20px, buttons ~16px, pills 999px). Bold, chunky, confident — but smart, not babyish (NIS students).
- **Mascot**: a small ORIGINAL friendly character (do NOT copy Duo the owl / any trademark) — e.g. a rounded encouraging creature/sprout. It reacts/encourages across the flow (speech bubbles, celebration). Simple inline SVG.
- **Gamification**: streak (flame), big rounded lesson progress bar, points/XP-like reward, celebratory feedback on closure.

## Color tokens — warm orange (not neon)
```
--bg:           #FFF8F1   /* warm cream, never pure white */
--surface:      #FFFFFF   /* cards */
--surface-soft: #FFF3E8
--text:         #2B2724   /* warm near-black */
--text-muted:   #8A817A
--border:       #ECE3D9   /* warm subtle border on cards */
--primary:      #EA580C   /* warm orange — main brand/CTA (orange-600, not neon) */
--primary-edge: #B8460B   /* darker bottom edge for 3D button press */
--on-primary:   #FFFFFF
--secondary:    #F59E0B   /* amber — streak/rewards */
--info:         #2A91C4   /* friendly blue — secondary/info actions */
--success:      #4F9D00   /* deep friendly green — "верно/готово" (AA on white) */
--success-edge: #3D7A00
--danger:       #DC2626   /* rare; mistakes are NOT framed as angry red */
```
Supportive mistake states (NEVER red): `--state-revisit:#2A91C4 (blue, «разберём»)`, `--state-almost:#F59E0B (amber, «почти»)`, `--state-got:#4F9D00 (green, «готово»)`.
Radii: `--r-card:18px`, `--r-button:16px`, `--r-pill:999px`. Card depth: `border:1.5px solid --border; box-shadow:0 2px 0 rgba(43,39,36,.05)`.

## Typography — rounded + FULL CYRILLIC (ru/kz), self-hosted woff2 incl. cyrillic subset
- Display / headings / numerals / button labels: **M PLUS Rounded 1c** 700/800/900 (chunky rounded, Duolingo-adjacent, cyrillic ✓).
- Body / supporting: **Nunito** 400/600/700/800 (cyrillic ✓, highly readable).
- NEVER Inter/Roboto/Arial. Inputs ≥16px. Tabular numerals for streak/points/counters.
- Math: KaTeX, `throwOnError:false`, `overflow-x:auto` on a WRAPPER div.

## Motion
- Animate only `transform`/`opacity`. Button mechanical press (above), ~120–180ms. Staggered list reveal 30–50ms/item. Celebration = spring/confetti on closure + mascot. `@media (prefers-reduced-motion: reduce)` disables non-essential motion.

## Information architecture
- Bottom nav ≤3 (label+icon, active highlighted in orange): **Учёба/Срез** · **Прогресс** · (later Профиль).
- **Hub:** top status row (streak flame + points). Mascot greeting with a growth-mindset line + today's срез summary + big rounded progress bar. Then error TILES (clean, flat, rounded, thin border): topic, the math (KaTeX), a SUPPORTIVE state pill (blue/amber/green, never red), big chunky 3D **«Разобрать»** button → `/drill/:id`. States: loading (skeleton), empty (celebratory + mascot), error (retry).
- **Drill (headline):** mascot + level intro (1 «разберём тему» / 2 «вспомним» / 3 «почти — проверим, где»); big problem card; vertical step **ladder** with «шаг 2 из 4» progress bar; hints reveal (never the answer); big chunky **«Сфотографировать решение»** button → diagnosis card: located step highlighted + collapsible transcription ("что я увидел" receipts) + supportive cause from the mascot. Worked step only as last resort.
- **Closure:** big celebration (confetti + mascot + points), verification solved hint-free → "ошибка закрыта".
- **Analytics:** friendly "твои частые ошибки" with chunky bars.

## Accessibility / mobile (must)
- Text contrast ≥4.5:1 (verify orange-on-white for text: use --primary for fills, darker for text-on-white). Touch targets ≥44px, 8px gaps. `viewport-fit=cover`, safe-area, `min-h-dvh`. Visible focus ring (orange). Color never the only signal. Reduced-motion + Dynamic Type safe.

## Tone
Mistake = «где растёт мозг». Mascot praises effort, never shames. No angry red. Encouraging, warm, gamified, a bit fun — smart, not babyish.
