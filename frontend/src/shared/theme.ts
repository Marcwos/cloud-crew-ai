import type { AgentId, AgentAction } from '../features/crew-office/domain/types'

// ── Agent metadata ─────────────────────────────────────────────────────────

export interface AgentMeta {
  id: AgentId
  /** Short display name (first name of pioneer) */
  name: string
  /** Full pioneer description shown in tooltip */
  tooltip: string
  /** Role / specialty */
  role: string
  /** Primary hex color */
  color: string
  /** Tailwind CSS variable or hex used for bg tint */
  colorVar: string
}

export const AGENT_META: Record<AgentId, AgentMeta> = {
  leslie: {
    id: 'leslie',
    name: 'Leslie',
    tooltip: 'Leslie Lamport — pioneer of distributed systems (LaTeX, Paxos)',
    role: 'Orchestrator',
    color: '#8B5CF6',
    colorVar: '--color-leslie',
  },
  alan: {
    id: 'alan',
    name: 'Alan',
    tooltip: 'Alan Turing — father of computer science and AI',
    role: 'Compute',
    color: '#3B82F6',
    colorVar: '--color-alan',
  },
  edgar: {
    id: 'edgar',
    name: 'Edgar',
    tooltip: 'Edgar F. Codd — inventor of the relational model',
    role: 'Data',
    color: '#10B981',
    colorVar: '--color-edgar',
  },
  hedy: {
    id: 'hedy',
    name: 'Hedy',
    tooltip: 'Hedy Lamarr — inventor of frequency-hopping spread spectrum',
    role: 'Security',
    color: '#EF4444',
    colorVar: '--color-hedy',
  },
  grace: {
    id: 'grace',
    name: 'Grace',
    tooltip: 'Grace Hopper — inventor of the first compiler',
    role: 'Monitoring',
    color: '#F59E0B',
    colorVar: '--color-grace',
  },
  vint: {
    id: 'vint',
    name: 'Vint',
    tooltip: 'Vint Cerf — co-creator of TCP/IP',
    role: 'Networks',
    color: '#06B6D4',
    colorVar: '--color-vint',
  },
}

// ── Action badge config ────────────────────────────────────────────────────

export interface ActionBadgeMeta {
  label: string
  /** Tailwind background color class */
  bgClass: string
  /** Tailwind text color class */
  textClass: string
  /** Extra animation class */
  animClass?: string
}

export const ACTION_BADGE: Record<AgentAction, ActionBadgeMeta> = {
  idle: {
    label: 'idle',
    bgClass: 'bg-slate-700',
    textClass: 'text-slate-400',
  },
  moving: {
    label: 'moving',
    bgClass: 'bg-yellow-900/60',
    textClass: 'text-yellow-400',
    animClass: 'badge-moving',
  },
  analyzing: {
    label: 'analyzing',
    bgClass: 'bg-blue-900/60',
    textClass: 'text-blue-400',
    animClass: 'badge-analyzing',
  },
  proposing: {
    label: 'proposing',
    bgClass: 'bg-emerald-900/60',
    textClass: 'text-emerald-400',
  },
  reviewing: {
    label: 'reviewing',
    bgClass: 'bg-orange-900/60',
    textClass: 'text-orange-400',
  },
  done: {
    label: '✓ done',
    bgClass: 'bg-emerald-900/80',
    textClass: 'text-emerald-300',
  },
}

// ── Specialist agent order (leslie is always first/top) ────────────────────

export const SPECIALIST_IDS: AgentId[] = ['alan', 'edgar', 'hedy', 'grace', 'vint']

// ── 2D office positions ────────────────────────────────────────────────────
// Coordinates are percentages of the office floor (x = left, y = top).
// Agents render absolutely-positioned; changing coords + a CSS transition
// makes them *walk* between their desk and the meeting table. No game loop.

export interface Point {
  x: number
  y: number
}

/** Where each agent sits when idle — desks around the room perimeter. */
export const HOME_POS: Record<AgentId, Point> = {
  leslie: { x: 50, y: 46 }, // central orchestrator station
  alan: { x: 30, y: 45 }, // compute station
  edgar: { x: 69, y: 45 }, // data station
  hedy: { x: 27, y: 69 }, // security station
  grace: { x: 72, y: 69 }, // monitoring and cost station
  vint: { x: 50, y: 84 }, // networking / API station
}

/** Where each agent gathers when active — a ring around the meeting table. */
export const MEETING_POS: Record<AgentId, Point> = {
  leslie: { x: 50, y: 34 }, // head of the table
  alan: { x: 33, y: 45 },
  edgar: { x: 33, y: 63 },
  hedy: { x: 50, y: 72 },
  grace: { x: 67, y: 63 },
  vint: { x: 67, y: 45 },
}

/** Center of the meeting table (for the static table marker). */
export const TABLE_CENTER: Point = { x: 50, y: 54 }

/**
 * Derive an agent's floor position from its current action.
 * Idle or finished → at their desk. Anything else → gathered at the table.
 */
export function agentFloorPosition(id: AgentId, action: AgentAction): Point {
  const gathered = action !== 'idle' && action !== 'done'
  return gathered ? MEETING_POS[id] : HOME_POS[id]
}
