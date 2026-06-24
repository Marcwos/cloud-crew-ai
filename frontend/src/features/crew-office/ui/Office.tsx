import { cn } from '../../../shared/cn'
import { AGENT_META, SPECIALIST_IDS } from '../../../shared/theme'
import { AgentSprite } from './AgentSprite'
import type { OfficeState } from '../domain/types'

interface OfficeProps {
  officeState: OfficeState
}

/**
 * The pixel-art office layout.
 *
 * Layout:
 *   ┌─────────────────────────────────────┐
 *   │       LESLIE  (top-center)          │  Leader desk
 *   ├──────┬──────┬──────┬──────┬────────┤
 *   │ ALAN │EDGAR │ HEDY │GRACE │  VINT  │  Specialist grid (2-3 cols)
 *   └──────┴──────┴──────┴──────┴────────┘
 */
export function Office({ officeState }: OfficeProps) {
  const leslieState = officeState.agents['leslie']
  const leslieMeta = AGENT_META['leslie']

  return (
    <section
      data-testid="office"
      className="office-layout"
      aria-label="Cloud Crew AI Office"
    >
      {/* ── Leader station (Leslie) ──────────────────────────────────── */}
      <div className="flex justify-center">
        <div
          className={cn(
            'station-card w-full max-w-sm',
            'relative overflow-visible'
          )}
          style={{
            borderColor: leslieMeta.color,
            backgroundColor: `${leslieMeta.color}11`,
          }}
        >
          {/* Leader badge */}
          <div
            className="station-header"
            style={{
              borderBottomColor: `${leslieMeta.color}44`,
              color: leslieMeta.color,
              backgroundColor: `${leslieMeta.color}18`,
            }}
          >
            <span className="opacity-60">◆</span>
            {' '}ORCHESTRATOR DESK
          </div>

          <div className="station-body flex justify-center py-6">
            <AgentSprite state={leslieState} isLeader />
          </div>

          {/* Status line */}
          {officeState.isRunning && !officeState.isDone && (
            <div className="px-4 pb-4 text-center">
              <span className="text-xs font-mono text-violet-400 badge-analyzing inline-block">
                coordinating crew…
              </span>
            </div>
          )}
          {officeState.isDone && (
            <div className="px-4 pb-4 text-center">
              <span className="text-xs font-mono text-emerald-400">
                ✓ mission complete
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Specialist stations grid ─────────────────────────────────── */}
      <div className="office-specialists-grid">
        {SPECIALIST_IDS.map((agentId) => {
          const agentState = officeState.agents[agentId]
          const meta = AGENT_META[agentId]

          return (
            <div
              key={agentId}
              className="station-card"
              style={{
                borderColor: meta.color,
                backgroundColor: `${meta.color}0d`,
              }}
            >
              {/* Station header */}
              <div
                className="station-header"
                style={{
                  borderBottomColor: `${meta.color}33`,
                  color: meta.color,
                  backgroundColor: `${meta.color}18`,
                }}
              >
                {meta.role.toUpperCase()}
              </div>

              {/* Agent sprite */}
              <div className="station-body flex justify-center py-5">
                <AgentSprite state={agentState} />
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Session ID indicator ─────────────────────────────────────── */}
      {officeState.sessionId && (
        <div className="flex justify-center">
          <span className="font-mono text-xs text-slate-600">
            session: {officeState.sessionId}
          </span>
        </div>
      )}

      {/* ── Live region — announces agent status changes to AT ───────── */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="false"
        className="sr-only"
      >
        {officeState.isRunning && !officeState.isDone && 'Crew is active and working on your challenge.'}
        {officeState.isDone && 'Mission complete. The crew has finished.'}
      </div>
    </section>
  )
}
