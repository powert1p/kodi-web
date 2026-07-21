import { describe, expect, it } from 'vitest'
import { hasJourneyWorkspace, type JourneyState } from '../lib/journeyApi'

const legacyState = {
  journey_id: 12,
  revision: 18,
  next_step: {
    type: 'independent_task',
    title: 'Реши самостоятельно',
    primary_action: 'Сфотографировать решение',
    mode: 'independent',
    problem: {
      id: 431,
      content_idx: 1765,
      node_id: 'PC06',
      statement: 'Найди новую концентрацию раствора.',
      topic: { id: 'PC06', title: 'Смеси и концентрации' },
    },
    instruction: 'Реши на бумаге.',
    photo_required: true,
    help_available: true,
    photo_consent_required: false,
  },
  context: {
    exam_map: { title: 'NIS', scope_note: 'Математика', day_one: [] },
    route: { topics: [], index: 0, completed: [] },
  },
} satisfies JourneyState

describe('journey workspace compatibility', () => {
  it('принимает полный v1 envelope', () => {
    const state = {
      ...legacyState,
      workspace_version: 1,
      task: {
        journey_id: 12,
        problem_id: 431,
        topic: { id: 'PC06', title: 'Смеси и концентрации' },
        mode: 'independent',
        statement: 'Найди новую концентрацию раствора.',
        position: 1,
      },
      learner_evidence: { kind: 'photo', status: 'empty', label: null },
      context_layer: { kind: 'closed', verdict: null, recovery_reason: null },
      response: { default_mode: 'photo', typed_available: false, help_available: true },
      support: { used: false, highest_hint_rung: 0 },
    } satisfies JourneyState

    expect(hasJourneyWorkspace(state)).toBe(true)
  })

  it('не ломает legacy response без envelope', () => {
    expect(hasJourneyWorkspace(legacyState)).toBe(false)
    expect(hasJourneyWorkspace({ ...legacyState, workspace_version: 1 })).toBe(false)
  })
})
