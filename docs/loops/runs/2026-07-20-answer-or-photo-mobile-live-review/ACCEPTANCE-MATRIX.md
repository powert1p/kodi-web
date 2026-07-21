# Executable acceptance matrix

| Case | Expected server state | Expected UI evidence | Gate |
|---|---|---|---|
| Exact typed correct | one accepted attempt; revision +1; next problem/stage; no photo requirement | pending ≤100 ms; success; next task focused | backend endpoint + deferred frontend + live AI |
| Equivalent typed correct | AI `correct` including `error_focus=format`; no local exact fallback; same terminal transition | same as exact | provider unit + endpoint + live `2 5/6`-style case |
| Typed needs revision | same task; safe feedback; first negative evidence recorded once; replay/outcome repeat does not duplicate it | draft preserved; retry/photo/help visible | backend evidence/replay + frontend |
| Typed uncertain | same task; fail-closed feedback; no evidence | retry/photo visible; no mathematical blame | backend + frontend |
| Provider 503 | persisted retryable state; processing lease cleared | explicit provider message; draft and retry retained | backend + frontend |
| Provider 429 | no progression/evidence; lease recoverable with same durable attempt | rate-limit message; draft, retry and photo alternative retained | backend + frontend interception |
| Offline/timeout | no server progress | visible local error; same draft/idempotency id; retry works | deferred frontend test + browser interception |
| Stale revision | 409 with authoritative state; no progress from stale payload | authoritative screen applied; visible refresh explanation | backend + frontend + browser |
| Double tap/replay | one attempt/transition; terminal replay stable | one pending state, one visible advance | concurrency/idempotency test |
| Correct photo | existing photo AI path remains a valid terminal alternative | no regression in upload, recovery or feedback | targeted backend + public live photo |
| 375×844 | no overflow/overlap; targets ≥44; task + action hierarchy intact | screenshot + DOM metrics + console/network clean | Playwright |
| 844×375 | short-landscape compact layout; every interactive rect inside viewport; viewport-anchored dock does not cover task/input/feedback; all actions reachable | screenshot, rect assertions and visual-viewport probe | Playwright |
| 932×430 | short-landscape compact layout across the 841–1152 px band; response rail and every action fully inside viewport | screenshot, rect assertions and visual-viewport probe | Playwright |
| 1280×900 | task dominant, readable math, one primary action | screenshot + DOM metrics | Playwright |
| Keyboard/focus | logical tab order; focus visible; new task receives focus after correct; OS keyboard never hides input/feedback/action | M2: proxy PASS; M3: public mobile WebKit + real macOS Accessibility Keyboard PASS — input and AI feedback captures, active `short-answer`, `visualViewport=844×375`, no overflow/errors | automated proxy + `evidence-public-webkit-keyboard-r6` release-device gate |
| Reduced motion | transition remains understandable at reduced motion | computed durations and success signal | Playwright |

Release is blocked by any P0/P1, horizontal overflow, hidden primary action, silent tap,
correct→same-task/photo transition, duplicate progress, console/request error or mismatch between
visible UI and server state.
