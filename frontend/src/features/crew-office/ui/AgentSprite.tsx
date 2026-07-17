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
  /** Temporary walk animation used until directional spritesheets are ready. */
  isWalking?: boolean
  /** Optional map interaction, currently used to open Leslie's mission dialogue. */
  onActivate?: () => void
}

export function AgentSprite({
  state,
  isLeader = false,
  compact = false,
  isWalking = false,
  onActivate,
}: AgentSpriteProps) {
  const meta = AGENT_META[state.id]
  const badge = ACTION_BADGE[state.action]

  // Station mode uses small sprites so they sit inside the characters shown
  // in the HUB artwork instead of covering the station signage.
  const spriteSize = compact
    ? isLeader ? 'w-16 h-16' : 'w-14 h-14'
    : isLeader ? 'w-28 h-28' : 'w-20 h-20'
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
        role={onActivate ? 'button' : 'img'}
        tabIndex={0}
        aria-label={`${meta.name} — ${meta.role}`}
        aria-describedby={tooltipId}
        className={cn(
          'pioneer-tooltip agent-avatar relative select-none',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 rounded-md',
          spriteSize,
          isWalking && 'is-walking',
          isActive && 'is-active'
        )}
        style={{
          // Colored aura only while the agent is working.
          filter: isActive ? `drop-shadow(0 0 7px ${meta.color}aa)` : undefined,
          ['--ring-color' as string]: meta.color,
        }}
        data-tooltip={meta.tooltip}
        title={meta.tooltip}
        onClick={onActivate}
        onKeyDown={(event) => {
          if (onActivate && (event.key === 'Enter' || event.key === ' ')) {
            event.preventDefault()
            onActivate()
          }
        }}
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

      {/* Agent info (hidden in station mode; the HUB artwork has its own labels) */}
      {!compact && <div className="flex flex-col items-center gap-1 text-center">
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
      </div>}
    </div>
  )
}
