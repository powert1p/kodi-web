# M2 live results — exact local candidate

Дата прогона: 2026-07-20 (Asia/Almaty).

Candidate:

- frontend: `http://127.0.0.1:5173/app/`;
- backend: `http://127.0.0.1:8414`;
- `/ready`: database, PWA и AI provider — `true`;
- браузер: Playwright Chromium, service workers blocked for deterministic checks.

## Answer-or-photo behavior

| Scenario | Live result |
|---|---|
| Correct typed answer | `350` for the 5%/15% mixture problem; real AI returned HTTP 200 in 1.075 s; the button immediately changed to `Проверяем…`; the journey advanced to `topic_result`; no photo requirement; result H1 received focus |
| Incorrect typed answer | `0` for the three-day tourist problem; real AI returned HTTP 200 in 1.236 s with `incorrect/calculation`; the same task and draft remained; photo and help stayed available |
| Offline | `/api/journey/answer` aborted with `ERR_INTERNET_DISCONNECTED`; draft `0` remained; explicit error, `Повторить проверку`, and photo alternative were visible |
| Rate limit | `/api/journey/answer` returned HTTP 429; draft `0` remained; rate-limit message, `Повторить проверку`, and photo alternative were visible |

Normal typed-correct and typed-incorrect runs had no page errors, console errors or
horizontal overflow. The console errors in offline/429 artifacts are the intentionally
injected failed requests and matched the visible recovery state.

## Responsive live review

After the user clicks `Ввести ответ`, the typed input is focused. In short landscape the
form scrolls as one unit, so the input and the primary action remain together.

| Viewport | Input rect (top..bottom) | Primary rect (top..bottom) | Visible | Overflow X | Runtime errors |
|---|---:|---:|---|---:|---|
| 375×844 | 676.4..726.4 | 732.8..780.8 | yes / yes | 0 | none |
| 844×375 | 220.2..270.2 | 276.5..324.5 | yes / yes | 0 | none |
| 932×430 | 275.2..325.2 | 331.5..379.5 | yes / yes | 0 | none |
| 1280×900 | 469.9..519.9 | 528.7..587.1 | yes / yes | 0 | none |
| keyboard proxy 375×500 | 332.4..382.4 | 388.8..436.8 | yes / yes | 0 | none |

All four main viewports were also exercised with `prefers-reduced-motion: reduce`.
The typed input remained the active element. The only sub-44 px DOM rectangle was the
hidden 1×1 file input; its visible upload button is a separate full-size control.

## Browser limitation

The installed Playwright WebKit build for this macOS runtime exits with `Bus error: 10`
before opening a page. This does not invalidate the Chromium M2 gate, but the release
device gate remains a public iPhone Safari or compatible mobile WebKit check after deploy,
as required by the acceptance matrix.

## Final acceptance delta

Fresh review found that the original provider-chain timeout could overlap a re-acquired
typed lease. The final candidate now uses one strict 40-second wall-clock boundary for the
whole AI chain. A provider task that suppresses `CancelledError` is cancelled and drained
without DB side effects; the router separately checks the exact lease before any attempt or
journey mutation. The regression test reproduces a cancellation-resistant provider and
proves that the HTTP path returns before the stale-lease boundary.

Post-delta live recheck on the restarted final backend:

- real Gemini incorrect `0`: HTTP 200 in 1.734 s; the same task remained, the draft was
  preserved and the feedback status received focus;
- real Gemini correct canonical `15`: HTTP 200 in 0.915 s; the journey advanced to
  `transfer_task`, the new heading received focus and `photo_required=false`;
- `Проверяем…` was observable for both requests; console and page error lists were empty;
- compact evidence: `/tmp/kodi-answer-photo-live-recheck/post-delta-summary.json`.

## Mechanical and independent gates

- backend with PostgreSQL: `706 passed, 28 warnings in 104.93s`;
- webapp tests: `20` files, `125` tests passed;
- production webapp build: passed;
- design lint: passed;
- Oxlint: exit 0; three pre-existing warnings only;
- `git diff --check` and Python compile for the changed backend modules: passed;
- fresh blind reviewer: `READY`, no P0/P1 findings in the strict deadline, detached-task
  drain, caller cancellation or typed lease/CAS path.
