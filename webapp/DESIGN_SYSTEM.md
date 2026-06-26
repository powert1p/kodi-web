# Kodi Error Trainer — Design System (v4, AiPlus)

> **Source of truth:** the framework-agnostic AiPlus spec at
> `/Users/esetseitkamal/Downloads/aiplus-design-system/aiplus-design-system.md`
> (§9.1 CSS variables, §3 type, §4 spacing, §5 radii, §6 shadows, §8 components).
> This doc summarizes the adoption; the spec wins on any conflict.
>
> Supersedes v3 ("Duolingo-style warm orange" with chunky-3D push-buttons) and the
> earlier v1 dark / v2 claymorphism. v4 adopts the owner's REAL product language: **AiPlus.**

## Direction — AiPlus flat-bordered clarity

- **Light theme is canon.** Background is **white `#FFFFFF`** (`--bg-primary`), never cream.
- **Surfaces are FLAT** — separated by **1px borders**, not shadows, not clay, not 3D edges.
  Shadows are rare (only the bottom bar, tooltip, menu, overlay per §6).
- **One brand color: orange `#FF8C00`** (`--bg-brand` / `--text-brand` / `--stroke-brand`).
  NOT the v3 `#EA580C`.
- Radii: **buttons/inputs 12** (`--radius-lg`), **cards 14** (`--radius-xl`), **chips/tags 8**
  (`--radius-sm`), **bottom-bar/dialog top 16**, **pill = full**.
- Spacing on a **4-grid** (4/8/12/16/20/24) with thin 2/6 steps.

## Typography — DM Sans + Onest (Cyrillic)

- Canonical face is **DM Sans** (400/500/700), `--font-sans: 'DM Sans','Onest',system-ui,sans-serif`.
- ⚠️ **Cyrillic gotcha:** the Google Fonts build of DM Sans (v17) ships **only latin / latin-ext —
  no Cyrillic subset**. This app is ru/kz, so Cyrillic would fall back to system-ui and break.
  **Fix:** self-host DM Sans (latin, carries the brand character + numerals) **+ Onest** (cyrillic /
  cyrillic-ext — a modern geometric grotesque whose character sits very close to DM Sans).
  `@font-face` `unicode-range` routes glyphs automatically: latin → DM Sans, Cyrillic → Onest.
  All four woff2 are self-hosted in `src/theme/fonts/` (offline-ready PWA). See `src/theme/fonts.css`.
- Type scale (`.text-h1/h2/h3/title/body/caption1/caption2/label-small` in `index.css`, §3):
  h1 32/38·700, h2 24/30·700, h3 20/24·500, title 16/22·500, body 16/24·400,
  caption1 14/20·400, caption2 12/16·400, label-small 11/16·500.

## Tokens

- Full AiPlus CSS custom properties (§9.1) live in `src/theme/tokens.css`:
  `--bg-*`, `--text-*`, `--stroke-*`, `--radius-*`, `--shadow-*` (all exact values).
- ⚠️ **`--text-tertiary` = WHITE** — only for text/icons on a COLORED fill (button, chip, badge,
  active pagination). NEVER on white (invisible).
- Tailwind v4 `@theme` (in the same file) maps tokens → utilities: `bg-bg-brand`, `text-text-primary`,
  `border-stroke-secondary`, `rounded-lg`, `font-sans`, etc.
  Gotcha: keep `*/`-bearing token names out of CSS comments (e.g. write "color/font/radius tokens",
  not `--color-*/--font-*`) — `*/` prematurely closes the comment and breaks dev PostCSS.

## Components (AiPlus §8) — shared in `src/components/`

- **ApButton** — flat. filled = `bg-brand` + white `text-tertiary`, hover → `bg-brand-hovered`;
  outlined = brand border/text, hover → `bg-light-brand-warning`; radius 12; sizes m=48/s=40/xs=32;
  `isError` / `isLoading` / `block`. NO 3D press, NO shadow. (Replaces the v3 `Button3D`.)
- **ApTextField** — radius 12, filled `bg-tertiary`, border `stroke-primary-disabled` (1px) →
  focus `stroke-brand` (1.5px); error `stroke-error`; label `text-secondary`.
- **ApLinearProgress** — h8/r4, track `stroke-secondary`, fill `stroke-brand`.
- **ApTag** — padding 8×4, radius 8, caption1; statuses default/error/primary/success/info.
- **ApInformer** — banner: padding 12, radius 12, 1px border; info/warning/success/error. Used for
  the diagnosis "found-the-step", hints, retry banner, and level intro.
- **ApBottomBar** — top radius 16, `--shadow-bottom-bar`, icon 22, label 11px.
  **SIGNATURE:** active tab swaps outline→filled icon, color lerps to `bg-brand`, scale ~1.15
  (`.ap-nav-icon` / `.ap-nav-active`). The one orchestrated branded motion; everything else is quiet.
- `.ap-card` utility (in `index.css`) — flat card: `bg-tertiary` + 1px `stroke-secondary`, radius 14.

## Icons — `src/icons/index.tsx`

AiPlus SVGs (from the spec's `icons/`) reproduced as React components with `currentColor` (so they
tint via `color`/tokens): Home/HomeActive, Task/TaskActive (nav), Left/Right/Down/LongArrowRight,
Close/Restart/CameraUpload(cloud_upload)/Eye/Search, Check/Star/StarFilled/Checklist/History.
Outline 1.5px (24) / 1.2px (16), filled variants for active states.

## Product personality (kept, lightly)

- Mascot **«Кёди»** (orange sprout, `src/components/Mascot.tsx`) retained as an illustrative accent,
  re-tinted to AiPlus tokens (`--bg-brand` / `--bg-success`). Greeting / diagnosis / closure / login.
- Supportive growth-mindset tone kept: a mistake is «где растёт мозг», NEVER a punishing red.
  State traffic-light maps to AiPlus tags: «разберём» = info (blue), «почти» = primary (brand),
  «готово» = success (green).
- Gamification rendered with AiPlus tags/pills/progress (streak, XP), not chunky game widgets.

## States & motion

- Every component ships loading (skeleton+shimmer) / empty (one line + CTA, celebratory) /
  error (component-level retry, no red, no apology) / hover / focus-visible (2px `stroke-brand` ring).
- One orchestrated page-load stagger (`.reveal`); content visible without JS. `prefers-reduced-motion`
  honored (reveal/stamp/confetti/bob/nav-scale all neutralized).

## Known AA notes (AiPlus-canonical values)

These ratios are defined by the AiPlus spec itself (kept faithfully, not deviated):
- white-on-`#FF8C00` button label = 2.33:1 — passes only as AA-large with large/bold labels;
- `text-brand` orange as TEXT on white (eyebrows/tag text) ≈ 2.33:1; `text-secondary #888` on white
  3.54:1 (AA-large). Body/heading `text-primary #090909` on white = 19.9:1 (AA).
  See the task report for the full audit.
