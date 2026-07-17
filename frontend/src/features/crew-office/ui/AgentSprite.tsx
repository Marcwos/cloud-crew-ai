import { cn } from '../../../shared/cn'
import { AGENT_META, ACTION_BADGE } from '../../../shared/theme'
import { AGENT_SPRITE } from '../../../assets/agents'
import type { AgentState } from '../domain/types'

interface AgentSpriteProps {
  state: AgentState
  /** Show larger card (used for leslie's leader position) */
  isLeader?: boolean
  /** Floor mode: hide the role line and tighten the message footprint */
  compact?: boolean
}

export function AgentSprite({ state, isLeader = false, compact = false }: AgentSpriteProps) {
  const meta = AGENT_META[state.id]
  const badge = ACTION_BADGE[state.action]

  const spriteSize = isLeader ? 'w-28 h-28' : 'w-20 h-20'
  const tooltipId = `tooltip-${state.id}`
  // "Active" = the agent is currently doing work (not resting at its desk).
  const isActive = state.action !== 'idle' && state.action !== 'done'

  return (
    <div
      data-testid={`agent-${state.id}`}
      className={cn(
        'flex flex-col items-center gap-3',
        isLeader && 'items-center'
      )}
    >
      {/* Pioneer description — visually hidden, exposed to AT via aria-describedby */}
      <span id={tooltipId} className="sr-only">
        {meta.tooltip}
      </span>

      {/* Pixel-art avatar — animated sprite */}
      <div
        role="img"
        tabIndex={0}
        aria-label={`${meta.name} — ${meta.role}`}
        aria-describedby={tooltipId}
        className={cn(
          'pioneer-tooltip agent-avatar relative select-none',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 rounded-md',
          spriteSize,
          isActive && 'is-active'
        )}
        style={{
          // Colored aura only while the agent is working.
          filter: isActive ? `drop-shadow(0 0 7px ${meta.color}aa)` : undefined,
          ['--ring-color' as string]: meta.color,
        }}
        data-tooltip={meta.tooltip}
        title={meta.tooltip}
      >
        <img
          src={AGENT_SPRITE[state.id]}
          alt=""
          aria-hidden
          draggable={false}
          className="pixel-sprite w-full h-full object-contain"
        />

        {/* Status indicator dot */}
        {state.action !== 'idle' && (
          <span
            className="absolute top-0 right-0 w-2.5 h-2.5 rounded-full border border-slate-900"
            style={{ backgroundColor: meta.color }}
            aria-hidden
          />
        )}
      </div>

      {/* Agent info */}
      <div
        className={cn(
          'flex flex-col items-center gap-1 text-center',
          compact && 'w-28'
        )}
      >
        {/* Name */}
        <span
          className={cn(
            'font-mono font-semibold leading-none',
            isLeader ? 'text-base' : 'text-sm'
          )}
          style={{ color: meta.color }}
        >
          {meta.name}
        </span>

        {/* Role */}
        {!compact && (
          <span className="text-xs text-slate-500 font-mono uppercase tracking-widest">
            {meta.role}
          </span>
        )}

        {/* Action badge */}
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-mono font-medium',
            badge.bgClass,
            badge.textClass,
            badge.animClass
          )}
        >
          {badge.label}
        </span>

        {/* Last message (if any) */}
        {state.message && (
          <p
            className={cn(
              'text-xs text-slate-400 text-center leading-tight mt-1',
              compact ? 'max-w-[110px] line-clamp-1' : 'max-w-[120px] line-clamp-2'
            )}
          >
            {state.message}
          </p>
        )}
      </div>
    </div>
  )
}
