import {
  AGENT_META,
  HOME_POS,
  TABLE_CENTER,
  agentFloorPosition,
} from '../../../shared/theme'
import { AgentSprite } from './AgentSprite'
import { AGENT_IDS } from '../domain/types'
import type { OfficeState } from '../domain/types'

interface OfficeProps {
  officeState: OfficeState
}

/**
 * The 2D office floor.
 *
 * Every agent is absolutely positioned. Its coordinates are DERIVED from its
 * current action (desk when idle/done, table when active). A CSS transition on
 * left/top interpolates the change, so the sprites *walk* — no game loop, no
 * animation frame, the browser tweens for us.
 */
export function Office({ officeState }: OfficeProps) {
  return (
    <section
      data-testid="office"
      className="office-floor"
      aria-label="Cloud Crew AI Office"
    >
      {/* ── Desk markers (static, one per home position) ─────────────── */}
      {AGENT_IDS.map((id) => {
        const meta = AGENT_META[id]
        const home = HOME_POS[id]
        return (
          <div
            key={`desk-${id}`}
            className="office-desk"
            style={{
              left: `${home.x}%`,
              top: `${home.y}%`,
              borderColor: `${meta.color}66`,
              backgroundColor: `${meta.color}0d`,
            }}
            aria-hidden
          >
            <span style={{ color: `${meta.color}aa` }}>{meta.role}</span>
          </div>
        )
      })}

      {/* ── Meeting table (static, center) ───────────────────────────── */}
      <div
        className="meeting-table"
        style={{ left: `${TABLE_CENTER.x}%`, top: `${TABLE_CENTER.y}%` }}
        aria-hidden
      >
        <span className="meeting-table-label">
          {officeState.isDone
            ? '✓ complete'
            : officeState.isRunning
              ? 'meeting'
              : 'crew table'}
        </span>
      </div>

      {/* ── Agents (absolute, walk between desk and table) ───────────── */}
      {AGENT_IDS.map((id) => {
        const agent = officeState.agents[id]
        const pos = agentFloorPosition(id, agent.action)
        const walking = agent.action !== 'idle'
        return (
          <div
            key={id}
            className="office-agent"
            style={{ left: `${pos.x}%`, top: `${pos.y}%`, zIndex: walking ? 20 : 10 }}
          >
            <AgentSprite state={agent} isLeader={id === 'leslie'} compact />
          </div>
        )
      })}

      {/* ── Session ID indicator ─────────────────────────────────────── */}
      {officeState.sessionId && (
        <span className="office-session-id font-mono">
          session: {officeState.sessionId}
        </span>
      )}

      {/* ── Live region — announces status changes to AT ─────────────── */}
      <div role="status" aria-live="polite" aria-atomic="false" className="sr-only">
        {officeState.isRunning && !officeState.isDone && 'Crew is active and working on your challenge.'}
        {officeState.isDone && 'Mission complete. The crew has finished.'}
      </div>
    </section>
  )
}
