import { useReducer, useState, useCallback, useRef, useEffect } from 'react'
import { agentReducer, createInitialOfficeState } from './agentReducer'
import type { OfficeState, FinalPlan, AgentEvent } from '../domain/types'
import type { ApiClient } from '../infrastructure/apiClient'
import type { SseClientFactory } from '../infrastructure/sseClient'

// ── Deps interface (dependency-injected for testability) ───────────────────

export interface UseCrewSessionDeps {
  apiClient: ApiClient
  sseClientFactory: SseClientFactory
  /** Called immediately for each validated SSE event, before visual consumers react to it. */
  onAgentEvent?: (event: AgentEvent) => void
}

// ── Hook return type ───────────────────────────────────────────────────────

export interface UseCrewSessionResult {
  officeState: OfficeState
  finalPlan: FinalPlan | null
  error: string | null
  startSession: (challenge: string) => Promise<void>
}

// ── Augmented reducer actions ──────────────────────────────────────────────

type ReducerAction =
  | { type: 'AGENT_EVENT'; payload: AgentEvent }
  | { type: 'SESSION_STARTED'; sessionId: string }
  | { type: 'SESSION_FAILED' }
  | { type: 'RESET' }

function officeReducer(state: OfficeState, action: ReducerAction): OfficeState {
  switch (action.type) {
    case 'AGENT_EVENT':
      return agentReducer(state, action.payload)

    case 'SESSION_STARTED':
      return {
        ...state,
        sessionId: action.sessionId,
        isRunning: true,
        isDone: false,
      }

    case 'SESSION_FAILED':
      return {
        ...state,
        isRunning: false,
      }

    case 'RESET':
      return createInitialOfficeState()

    default:
      return state
  }
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useCrewSession({
  apiClient,
  sseClientFactory,
  onAgentEvent,
}: UseCrewSessionDeps): UseCrewSessionResult {
  const [officeState, dispatch] = useReducer(
    officeReducer,
    undefined,
    createInitialOfficeState
  )
  const [finalPlan, setFinalPlan] = useState<FinalPlan | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Keep a ref to the SSE cleanup fn so we can abort on re-runs or unmount
  const sseCleanupRef = useRef<(() => void) | null>(null)

  // Close the SSE connection when the hook unmounts
  useEffect(() => () => { sseCleanupRef.current?.() }, [])

  const startSession = useCallback(
    async (challenge: string) => {
      // Reset any previous state
      dispatch({ type: 'RESET' })
      setFinalPlan(null)
      setError(null)

      // Abort previous SSE connection if any
      sseCleanupRef.current?.()

      let sessionId: string

      try {
        const result = await apiClient.createSession(challenge)
        sessionId = result.session_id
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err)
        setError(message)
        return
      }

      // Capture the active session id to guard against stale async resolutions
      const activeSessionId = sessionId

      // Mark session as running
      dispatch({ type: 'SESSION_STARTED', sessionId })

      // Open SSE stream
      const cleanup = sseClientFactory.create(
        `/api/sessions/${sessionId}/events`,
        (event: AgentEvent) => {
          dispatch({ type: 'AGENT_EVENT', payload: event })
          onAgentEvent?.(event)
        },
        () => {
          // onDone callback — leslie/done was received; fetch the full session
          apiClient
            .getSession(activeSessionId)
            .then((session) => {
              // Ignore if a new session has already started
              if (session.session_id !== activeSessionId) return
              if (session.final_plan) {
                setFinalPlan(session.final_plan)
              }
            })
            .catch((err: unknown) => {
              const message = err instanceof Error ? err.message : String(err)
              setError(message)
            })
        },
        (message: string) => {
          // onError callback — SSE stream dropped
          dispatch({ type: 'SESSION_FAILED' })
          setError(message)
        }
      )

      sseCleanupRef.current = cleanup
    },
    [apiClient, onAgentEvent, sseClientFactory]
  )

  return { officeState, finalPlan, error, startSession }
}
