import { agentFloorPosition } from '../../../shared/theme'
import type { AgentMotion } from '../application/useAgentMovement'
import { AgentSprite } from './AgentSprite'
import { ThoughtBubble } from './ThoughtBubble'
import { AGENT_IDS } from '../domain/types'
import type { AgentId, OfficeState } from '../domain/types'

interface OfficeProps {
  officeState: OfficeState
  motions?: Record<AgentId, AgentMotion>
  onAgentSelect?: (agent: AgentId) => void
}

/**
 * The 2D office floor.
 *
 * Every agent is absolutely positioned. Its coordinates are DERIVED from its
 * current action (desk when idle/done, table when active). A CSS transition on
 * left/top interpolates the change, so the sprites *walk* — no game loop, no
 * animation frame, the browser tweens for us.
 */
export function Office({ officeState, motions, onAgentSelect }: OfficeProps) {
  return (
    <section
      data-testid="office"
      className="office-floor"
      aria-label="Cloud Crew AI Office"
    >
      {/* ── Agents (absolute, walk between desk and table) ───────────── */}
      {AGENT_IDS.map((id) => {
        const agent = officeState.agents[id]
        const motion = motions?.[id]
        const pos = motion ?? agentFloorPosition(id, agent.action)
        const walking = motion?.isWalking ?? agent.action !== 'idle'
        return (
          <div
            key={id}
            className="office-agent"
            style={{ left: `${pos.x}%`, top: `${pos.y}%`, zIndex: walking ? 20 : 10 }}
          >
            {motion?.thought && <ThoughtBubble message={motion.thought} />}
            <AgentSprite
              state={agent}
              isLeader={id === 'leslie'}
              compact
              isWalking={walking}
              onActivate={id === 'leslie' ? () => onAgentSelect?.(id) : undefined}
            />
          </div>
        )
      })}

      {/* ── Live region — announces status changes to AT ─────────────── */}
      <div role="status" aria-live="polite" aria-atomic="false" className="sr-only">
        {officeState.isRunning && !officeState.isDone && 'Crew is active and working on your challenge.'}
        {officeState.isDone && 'Mission complete. The crew has finished.'}
      </div>
    </section>
  )
}
