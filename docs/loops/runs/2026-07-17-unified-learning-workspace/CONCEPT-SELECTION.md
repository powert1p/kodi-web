# Selected direction — C `Нить решения`

## Product promise

After a topic begins, the learner stays in one workspace until the learning cycle ends. The full
problem remains visible while the learner submits a photo or typed response, receives an AI
verdict, asks for a hint, talks to the task-scoped tutor, corrects work and moves to transfer.

The interface should feel like a clear mathematical proof being assembled, not a collection of
features, chat destinations or full-screen stage replacements.

## Stable composition

```text
SessionStrip ──────────────────────────────────────────────
       ● TaskAnchor ───── ● ContextualLayer ───── ● ResponseDock
          full problem       feedback/help          one next action
```

### Desktop, 1280+

- A wide but bounded learning canvas with three connected zones.
- `TaskAnchor` receives the most width and visual weight; the mathematical statement is the
  largest content on the page.
- `ContextualLayer` occupies the middle segment only when it has evidence, recovery, hint or tutor
  content. Its mint surface remains quieter than the paper surface.
- `ResponseDock` is the final segment of the same trace, not a detached sidebar. It holds one
  primary action and at most two compact secondary actions.
- Eye order is statement → learner work → AI evidence → next action. The thread and numbered
  markers make that order explicit without stepper chrome.

### Mobile, 375+

- The same trace becomes vertical; no persistent side rail and no horizontal carousel.
- The full statement remains above the current learner evidence. Context appears directly below
  the relevant evidence point.
- The response dock remains reachable at the bottom, but content receives enough bottom padding
  to prevent obstruction.
- `tutor_open` is an anchored sheet above the dock, not a new route. It keeps the problem visible
  and exposes provenance, grounded question, response field, send and close/continue controls.
- Only the active contextual segment expands. Completed/available segments are short markers,
  not large cards.

## Visual language

### Carry forward

- Warm paper background with dark green mathematical text.
- Orange only for the current action, active marker and small brand punctuation.
- Mint only for AI/context surfaces; it must never dominate the task statement.
- Dotted/segmented proof-thread as the product signature.
- Editorial mathematical hierarchy from concept A: large statement, restrained labels and
  generous leading.
- Explicit micro-labels from concept B where they improve orientation: `Твоя работа`,
  `AI-проверка`, `Следующее действие`.

### Do not carry forward

- Old logo used as a large decorative asset or copied one-to-one.
- A mascot as a navigation or feedback crutch.
- Bright color blocks behind every function.
- Dashboard/card soup, bottom navigation during an active task, floating universal AI chat,
  full-screen feedback pages or success confetti replacing evidence.
- The 48 px mobile rail from concept B.
- Generic gradients, glassmorphism or an “AI assistant” identity detached from the current task.

## Typography and density

- Use one Cyrillic-proven sans family for interface copy and one restrained editorial face for
  mathematical emphasis only if build/render proof confirms it.
- Mobile statement: minimum 24 px effective size; desktop: 34–48 px depending on length.
- Body copy: minimum 16 px; interactive labels: minimum 15 px; tap targets: minimum 44×44 px.
- Feedback headline is one line when possible; evidence is limited to three short lines before
  progressive disclosure.
- Prefer vertical whitespace and rules over nested containers. A surface exists only when it
  communicates state or interaction.

## Component contract

### `LearningWorkspace`

Owns stable geometry only. It receives authoritative `JourneyState` and projects the server stage
into the four zones. It never derives a second learning stage from local state.

### `SessionStrip`

Shows topic, mode, task position and save/connection status. It has no competing navigation while
an attempt is active. Exit is explicit and preserves the authoritative journey.

### `TaskAnchor`

Keeps `journey_id`, `problem_id`, statement, topic and current learner evidence mounted across
processing, feedback, hint, tutor and recovery. A new transfer problem may replace its content;
layer changes may not.

### `ContextualLayer`

Renders exactly one of:

- processing status;
- `correct` evidence;
- `needs_revision` localization and reason;
- `uncertain` recovery reason;
- hint rung H1–H4;
- task-scoped tutor thread;
- guided micro-step.

Opening and closing a layer returns focus to its invoker. A new AI message uses polite live
announcement; blocking recovery uses an alert only when progress is impossible.

### `ResponseDock`

Photo is the default, mastery-capable mode. Typed answer is always visible as a formative
alternative. The dock has one primary action per state and preserves a compatible draft by
`journey_id + problem_id + revision`.

## State application

| State | Thread segment | Primary action | Required preservation |
|---|---|---|---|
| `independent` | Task → work → action | `Добавить фото` | Full statement, typed alternative, help entry |
| `photo_ready` | Learner evidence active | `Отправить решение` | Preview/name, replace/remove |
| `processing` | AI evidence pending | none/disabled | Problem and submitted evidence |
| `correct` | Completed evidence segment | `Продолжить` | Why it is correct, mastery effect |
| `needs_revision` | First divergence marked | `Исправить решение` | Attempt, failed step, hint/tutor access |
| `typed_feedback` | Formative marker | `Сфотографировать полное решение` | Typed draft and feedback; no mastery claim |
| `hint_h1…h4` | Context branch on current step | `Вернуться к решению` | Current rung, support status, no answer leak |
| `tutor_open` | Anchored context branch | `Отправить помощнику` | Task provenance, thread, close path |
| `uncertain` | Interrupted evidence segment | `Переснять фото` | Preserved attempt, explicit no-verdict message |
| `guided_step` | Supported micro-step | `Проверить шаг` | Earlier context, step number, practice-only label |
| `transfer` | New task on same trace | `Отправить самостоятельное решение` | Support eligibility and fresh evidence requirement |

## Motion

- Geometry remains stable; only the active trace segment expands/collapses.
- Use 160–220 ms opacity/height transitions with no spring overshoot.
- Processing uses a subtle progress movement inside the evidence segment, not a page skeleton.
- Respect `prefers-reduced-motion`; state and reading order must remain complete without motion.

## Implementation boundary

The prototype is a visual/state reference, not production code. Production must reuse the live
React journey, FastAPI authority, revision/idempotency logic and database models. Before behavior
changes, add an ADR that records AI-owned semantic verdicts and synchronize the conflicting old
wording in `docs/VISION.md` and architecture docs.
