# Fable planning review

- Verdict: `REVISE`.
- Reviewer: `claude-fable-5`, effort `xhigh`, read-only runner.
- Reviewed packet: `PLANNING-PACKET.md` before freeze.
- One allowed planning delta applied before contract freeze.

## Required changes received

1. Replace one-state evidence with five-state matrix per direction and viewport.
2. Map durable legacy verdicts/stages to `correct | needs_revision | uncertain + reason`.
3. Define `typed_feedback` outcome: no transfer and no mastery; primary remains photo proof.
4. Resolve hint→mastery and transfer-help policy.
5. Override legacy screenshot set in run rubric and hash it before concepts.

## Resolution

- Frozen matrix: `independent`, `needs_revision`, `hint_h2`, `tutor_open`, `uncertain` × two
  viewports × three directions.
- Legacy mapping is in `STATE-MAP.md` and `AI-UX-CONTRACT.md`.
- Typed correct stays in the current task and asks for a full-solution photo.
- Opening help is neutral; receiving any H1–H4/tutor response marks current task supported and
  ineligible for mastery. Help is available in transfer, but then a new transfer is required.
- `RUBRIC.md` explicitly replaces `hub/drill/srez` for this workspace-only concept round.

A fresh Terra planning verifier must check only closure of these changes and preservation of the
invariants before freeze.
