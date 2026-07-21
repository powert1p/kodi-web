# Unified learning workspace — production result

## Verdict

`READY` and deployed on 2026-07-17.

- Public URL: <https://observer-terrorists-reputation-chosen.trycloudflare.com/app/>
- Frozen visual bar: passed, average `8.8`; every axis is at least `8.0`, math focus is
  `9.0`, premium distinctiveness is `8.6`.
- Fresh implementation review: `READY`, open P0/P1 `0`.

## Acceptance deltas

The first blind review found two visible blockers: incorrect-photo feedback exposed `15%`, and the
mobile tutor covered the task question. The bounded correction now uses a non-answer direction and
places the tutor inline below the stable task anchor.

A fresh implementation review then found an old fallback path that still reset document scroll and
focus. The safety correction excludes every practice state from that reset while retaining the
intentional onboarding transition. Regression tests cover both current workspace and legacy
practice continuity.

## Mechanical and live evidence

- Backend: `697 passed` on the isolated PostgreSQL suite after every acceptance correction.
- Frontend: `119 passed`; lint exits `0` with three pre-existing warnings; design lint clean;
  production build clean.
- Local state matrix: `PASS`, 42 states, 84 screenshots at 375x844 and 1280x900.
- Local live CJM: `PASS`; real tutor, typed grading and five Gemini photo calls; mastery only from
  full-solution photos.
- Production live CJM: `PASS`; two new learners received different routes, exact diagnostic and
  guided resume passed, the tutor withheld the final answer, typed evidence stayed formative, and
  final photo mastery reached `0.999`.
- Production state matrix: `PASS`, 42 states, 84 screenshots; no horizontal overflow, undersized
  controls, console errors, page errors, request errors or API errors.

The Python Playwright runner emitted `Target closed` cleanup warnings after closing temporary pages.
They are harness shutdown noise: both live gates exited `0`, and their captured console, page,
request and API error arrays are empty.

## Deployment evidence

- Candidate: `kodi-web:unified-workspace-r20-amd64` (`linux/amd64`).
- Local/remote normalised image fingerprint:
  `b20cf662e59347b38d5aa02ae97618511a1f9fbf3b933d6e288bc7cc91dfdb83`.
- Exact-image smoke: database, PWA and AI provider all ready; restart count `0`.
- Cutover: `2026-07-17T14:45:18Z`.
- Rollback tag: `kodi-web:rollback-pre-unified-r20-20260717T144518Z`.
- After the full public CJM: app `running/healthy`, tunnel `running`, both restart counts `0`, and
  zero `ERROR`, `CRITICAL`, `Traceback`, exception or HTTP 5xx log matches since cutover.

The cutover changed only the application image. It did not recreate PostgreSQL, restart the tunnel,
delete learner data or remove uploaded photos.
