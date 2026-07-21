# Benchmark contract — adaptive photo-first NIS

- **Objective:** превратить React PWA из direct-to-one-lesson demo в production-ready
  персональную подготовку к математическим блокам NIS с photo-first самостоятельной работой.
- **Run type:** production product + redesign generator-loop.
- **Scope:** registration/login, onboarding, official-format map, adaptive diagnostic, result,
  personalized route, explicit lesson start, whole-solution photo verdict, guided typed mode,
  transfer photo, persistence/resume, public deployment.
- **Non-goals:** языки/естествознание, live tablet/voice, teacher cabinet redesign, новый mascot
  character, копирование старого логотипа.
- **Frozen truth:** `BRIEF.md`, `RESEARCH.md`, пользовательский Goal-файл и authoritative
  `docs/VISION.md`; текущий React/backend — behavior evidence, а не достаточный продукт.
- **Frozen concepts:** `CONCEPTS.md`; root Codex последовательно собирает три renderable
  направления, reviewers остаются read-only.
- **Frozen quality bar:** `RUBRIC.md`; каждая ось ≥8, среднее ≥8.5, math/premium ≥8.5,
  critical flags 0, три explicit production `READY`, минимум 2/3 `wow`.
- **Target devices:** 375×844 и 1280×900.
- **Concept states:** route, photo-task, guided; один одинаковый fixture.
- **Production state matrix:** register, onboarding, map, diagnostic start/answer/resume/error,
  result, two distinct personalized routes, photo consent, upload/processing/unreadable/uncertain/
  correct/incorrect, guided/resume, transfer/mastery, relogin, empty/offline/reduced-motion.
- **Mechanical gates:** backend tests; frontend lint/design-lint/typecheck/tests/build; real browser
  console/network/overflow/keyboard/touch; live Gemini canary; server migration and public smoke.
- **Evidence order:** mechanics → root own-eyes → immutable snapshot → blind judges.
- **Stop policy:** owner stop, READY, or proven plateau of two blind delta rounds. Plateau/budget
  below bar is `NOT_READY/UNCERTAIN`, never a softened READY.

## Frozen hashes

Набор `freeze-1`, создан до первого concept maker:

```text
413ef627a95ba9a80a009820ed2c3c662c6ed6f101e7b091c701bb88f14c8a0c  BRIEF.md
8a4e53a154d92167d5110362021a0444887ac677c10c92de20422d5fe3991774  RESEARCH.md
bdebe1ffce0ab84fbaff6f1b86dddbec826d64e72607776659fec6105638450e  CONCEPTS.md
3c0e63965dad286b7f59619beda46e42f640fc3706bafb75dbef4d2757d6ac13  RUBRIC.md
2295490b1a8d806c1df5207607d97d89a4dfeac33e9f1843420cf27844cd90b8  pasted-text-1.txt
96cac33b8134b15d765f8888e2edb947f70f17210fe7c181733e4361aa318309  docs/VISION.md
```

Изменение любого frozen input требует нового hash set и fresh gates.
