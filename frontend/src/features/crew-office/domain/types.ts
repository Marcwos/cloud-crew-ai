// ============================================================
// Cloud Crew AI — Domain Types
// Pure TypeScript — no framework dependencies
// ============================================================

/** The six agents that form the Cloud Crew */
export type AgentId = 'leslie' | 'alan' | 'edgar' | 'hedy' | 'grace' | 'vint'

/** What an agent is currently doing */
export type AgentAction =
  | 'idle'
  | 'moving'
  | 'analyzing'
  | 'proposing'
  | 'reviewing'
  | 'done'

/** A single event received from the SSE stream */
export interface AgentEvent {
  agent: AgentId
  action: AgentAction
  status: string
  message: string
  /** Concrete task assigned by Leslie, present for specialist assignment events. */
  assignment?: string
}

/** Per-agent view state inside the office */
export interface AgentState {
  id: AgentId
  action: AgentAction
  status: string
  message: string
}

/** Global office state managed by the reducer */
export interface OfficeState {
  agents: Record<AgentId, AgentState>
  sessionId: string | null
  isRunning: boolean
  isDone: boolean
}

/** Final plan returned after the session completes */
export interface FinalPlan {
  summary: string
  services: string[]
  justification_by_service: Record<string, string>
  diagram_hint: string
}

/** Full crew session from the API */
export interface CrewSession {
  session_id: string
  challenge: string
  final_plan: FinalPlan | null
}

/** All valid agent IDs as a typed tuple — use for iteration / validation */
export const AGENT_IDS: readonly AgentId[] = [
  'leslie',
  'alan',
  'edgar',
  'hedy',
  'grace',
  'vint',
] as const

/** Type guard: checks if a string is a valid AgentId */
export function isAgentId(value: string): value is AgentId {
  return (AGENT_IDS as readonly string[]).includes(value)
}

/** Type guard: checks if a string is a valid AgentAction */
export function isAgentAction(value: string): value is AgentAction {
  const validActions: AgentAction[] = [
    'idle',
    'moving',
    'analyzing',
    'proposing',
    'reviewing',
    'done',
  ]
  return validActions.includes(value as AgentAction)
}
