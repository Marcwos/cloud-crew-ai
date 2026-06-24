import type { AgentEvent } from '../domain/types'
import { isAgentId, isAgentAction } from '../domain/types'

/**
 * Parses a raw SSE data string into a typed AgentEvent.
 *
 * Throws a descriptive Error if:
 *   - The string is not valid JSON
 *   - Required fields are missing
 *   - agent or action values are not in the valid enum sets
 *
 * Extra fields in the JSON are silently ignored.
 */
export function parseAgentEvent(data: string): AgentEvent {
  let raw: unknown

  try {
    raw = JSON.parse(data)
  } catch {
    throw new Error(`parseAgentEvent: invalid JSON — ${data}`)
  }

  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    throw new Error('parseAgentEvent: expected a JSON object')
  }

  const obj = raw as Record<string, unknown>

  // Validate 'agent' field
  if (!('agent' in obj)) {
    throw new Error('parseAgentEvent: missing required field "agent"')
  }
  if (typeof obj['agent'] !== 'string') {
    throw new Error('parseAgentEvent: field "agent" must be a string')
  }
  if (!isAgentId(obj['agent'])) {
    throw new Error(
      `parseAgentEvent: invalid agent value "${obj['agent']}" — must be one of leslie, alan, edgar, hedy, grace, vint`
    )
  }

  // Validate 'action' field
  if (!('action' in obj)) {
    throw new Error('parseAgentEvent: missing required field "action"')
  }
  if (typeof obj['action'] !== 'string') {
    throw new Error('parseAgentEvent: field "action" must be a string')
  }
  if (!isAgentAction(obj['action'])) {
    throw new Error(
      `parseAgentEvent: invalid action value "${obj['action']}" — must be one of idle, moving, analyzing, proposing, reviewing, done`
    )
  }

  // Coerce optional string fields with safe fallback
  const status = typeof obj['status'] === 'string' ? obj['status'] : ''
  const message = typeof obj['message'] === 'string' ? obj['message'] : ''

  // Return ONLY the known fields (no extra field contamination)
  return {
    agent: obj['agent'],
    action: obj['action'],
    status,
    message,
  }
}
