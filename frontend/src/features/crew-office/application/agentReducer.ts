import type { AgentId, AgentEvent, AgentState, OfficeState } from '../domain/types'
import { AGENT_IDS, isAgentId } from '../domain/types'

// ── Initial state factory ──────────────────────────────────────────────────

export function createInitialOfficeState(): OfficeState {
  const agents = Object.fromEntries(
    AGENT_IDS.map((id): [AgentId, AgentState] => [
      id,
      { id, action: 'idle', status: '', message: '' },
    ])
  ) as Record<AgentId, AgentState>

  return {
    agents,
    sessionId: null,
    isRunning: false,
    isDone: false,
  }
}

// ── Reducer ────────────────────────────────────────────────────────────────

/**
 * Pure reducer: (OfficeState, AgentEvent) → OfficeState
 *
 * Rules:
 * - Never mutates input state
 * - Unknown agent ids are ignored (defensive, type-safe)
 * - leslie + done sets isDone=true and isRunning=false
 */
export function agentReducer(state: OfficeState, event: AgentEvent): OfficeState {
  // Defensive guard: ignore events from agents we don't recognise
  if (!isAgentId(event.agent)) {
    return state
  }

  const updatedAgent: AgentState = {
    id: event.agent,
    action: event.action,
    status: event.status,
    message: event.message,
  }

  const isDoneTrigger = event.agent === 'leslie' && event.action === 'done'

  return {
    ...state,
    agents: {
      ...state.agents,
      [event.agent]: updatedAgent,
    },
    ...(isDoneTrigger
      ? { isDone: true, isRunning: false }
      : {}),
  }
}
