import { useCallback, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { postConsent } from '../../lib/api'
import { useLearningIdentity } from '../../lib/api'
import { compressForUpload } from '../../lib/image'
import {
  JourneyApiError,
  continueJourney,
  fetchJourney,
  requestJourneyHelp,
  retryJourneyPhoto,
  saveJourneyProfile,
  saveJourneyProfileDraft,
  submitDiagnosticAnswer,
  submitGuidedAnswer,
  submitTypedAnswer,
  uploadJourneyPhoto,
  type JourneyProfileInput,
  type JourneyState,
} from '../../lib/journeyApi'

export interface JourneyIssue {
  code: string
  message: string
  status: number
}

type AuthoritativeStateHandler = (state: JourneyState, issue: JourneyIssue) => void
type AmbiguousRecoveryPredicate = (state: JourneyState) => boolean

function attemptId(prefix: string): string {
  const id = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${prefix}-${id}`.slice(0, 64)
}

function issueFrom(error: unknown): JourneyIssue {
  if (error instanceof JourneyApiError) {
    return { code: error.code, message: error.message, status: error.status }
  }
  return {
    code: 'request_failed',
    message: error instanceof Error ? error.message : 'Не удалось выполнить действие. Попробуй ещё раз.',
    status: 0,
  }
}

export function useJourney() {
  const identity = useLearningIdentity()
  const queryClient = useQueryClient()
  const queryKey = useMemo(() => ['student-journey', identity] as const, [identity])
  const query = useQuery({
    queryKey,
    queryFn: fetchJourney,
    staleTime: 0,
    refetchInterval: (current) => (
      current.state.data
      && ['photo_processing', 'typed_processing', 'guided_processing'].includes(current.state.data.next_step.type)
        ? 1500
        : false
    ),
  })
  const [pendingAction, setPendingAction] = useState<string | null>(null)
  const [issue, setIssue] = useState<JourneyIssue | null>(null)
  const pendingRef = useRef(false)
  const durableAttempts = useRef(new Map<string, string>())

  const durableAttempt = useCallback((key: string): string => {
    const existing = durableAttempts.current.get(key)
    if (existing) return existing
    const created = attemptId(key.split(':', 1)[0] || 'attempt')
    durableAttempts.current.set(key, created)
    return created
  }, [])

  const perform = useCallback(async (
    action: string,
    operation: () => Promise<JourneyState>,
    durableKey?: string,
    onAuthoritativeState?: AuthoritativeStateHandler,
    recoverAmbiguous?: AmbiguousRecoveryPredicate,
  ): Promise<JourneyState | null> => {
    if (pendingRef.current) return null
    pendingRef.current = true
    setPendingAction(action)
    setIssue(null)
    try {
      const result = await operation()
      queryClient.setQueryData(queryKey, result)
      if (durableKey) durableAttempts.current.delete(durableKey)
      return result
    } catch (error) {
      if (error instanceof JourneyApiError && error.state) {
        queryClient.setQueryData(queryKey, error.state)
        const nextIssue = issueFrom(error)
        setIssue(nextIssue)
        onAuthoritativeState?.(error.state, nextIssue)
        return null
      }
      const nextIssue = issueFrom(error)
      if (recoverAmbiguous) {
        try {
          const recovered = await queryClient.fetchQuery({
            queryKey,
            queryFn: fetchJourney,
            staleTime: 0,
            retry: false,
          })
          queryClient.setQueryData(queryKey, recovered)
          if (recoverAmbiguous(recovered)) {
            setIssue(null)
            return null
          }
        } catch {
          // Ни исходная ошибка, ни сохранённый attempt не теряются: повтор
          // использует тот же durable client_attempt_id.
        }
      }
      setIssue(nextIssue)
      return null
    } finally {
      pendingRef.current = false
      setPendingAction(null)
    }
  }, [queryClient, queryKey])

  const state = query.data ?? null
  const revision = state?.revision ?? 0

  return {
    state,
    identity,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    loadError: query.error ? issueFrom(query.error) : null,
    issue,
    pendingAction,
    clearIssue: () => setIssue(null),
    refresh: () => {
      setIssue(null)
      return query.refetch()
    },
    saveProfile: (profile: JourneyProfileInput) => perform('profile', () => saveJourneyProfile({
      revision,
      target: 'nis-grade-7',
      language: 'ru',
      ...profile,
    })),
    saveProfileDraft: (
      profile: JourneyProfileInput,
      screen: 0 | 1 | 2 | 3,
      substep: 0 | 1 | 2 = 0,
    ) => perform('profile-draft', () => saveJourneyProfileDraft({
      revision,
      screen,
      substep,
      target: 'nis-grade-7',
      language: 'ru',
      ...profile,
    })),
    continueWith: (action: string, revisionOverride = revision) => perform(action, () => continueJourney({
      revision: revisionOverride,
      action,
    })),
    answerDiagnostic: (questionId: number, answer: string) => {
      const key = `diagnostic:${revision}:${questionId}:${answer}`
      return perform('diagnostic-answer', () => submitDiagnosticAnswer({
        revision,
        question_id: questionId,
        answer,
        client_attempt_id: durableAttempt(key),
      }), key)
    },
    askForHelp: (problemId: number) => perform('help', () => requestJourneyHelp({
      revision,
      problem_id: problemId,
    })),
    answerGuided: (problemId: number, stepNumber: number, answer: string) => {
      const key = `guided:${revision}:${problemId}:${stepNumber}:${answer}`
      return perform('guided-answer', () => submitGuidedAnswer({
        revision,
        problem_id: problemId,
        step_n: stepNumber,
        answer,
        client_attempt_id: durableAttempt(key),
      }), key, undefined, (recovered) => {
        if (recovered.next_step.type === 'guided_processing') return true
        if (
          recovered.next_step.type === 'guided_step'
          && recovered.next_step.feedback !== null
        ) return true
        return recovered.revision !== revision
      })
    },
    answerTyped: (
      problemId: number,
      answer: string,
      onAuthoritativeState?: AuthoritativeStateHandler,
    ) => {
      const key = `typed:${revision}:${problemId}:${answer}`
      return perform('typed-answer', () => submitTypedAnswer({
        revision,
        problem_id: problemId,
        answer,
        client_attempt_id: durableAttempt(key),
      }), key, onAuthoritativeState, (recovered) => {
        if (recovered.next_step.type === 'typed_processing') return true
        if (
          (recovered.next_step.type === 'independent_task' || recovered.next_step.type === 'transfer_task')
          && recovered.next_step.typed_feedback
        ) return true
        return recovered.revision !== revision
      })
    },
    uploadPhoto: (
      problemId: number,
      photo: File,
      revisionOverride = revision,
      clientAttemptId = attemptId('photo'),
    ) => perform('photo', async () => {
      const compressed = await compressForUpload(photo)
      const upload = compressed === photo
        ? photo
        : new File([compressed], photo.name, {
            type: compressed.type || photo.type,
            lastModified: photo.lastModified,
          })
      return uploadJourneyPhoto({
        revision: revisionOverride,
        problem_id: problemId,
        client_attempt_id: clientAttemptId,
        photo: upload,
      })
    }),
    retryPhoto: () => perform('photo-retry', () => retryJourneyPhoto({ revision })),
    grantPhotoConsent: () => perform('consent', async () => {
      await postConsent(true)
      return fetchJourney()
    }),
  }
}
