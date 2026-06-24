import { cn } from '../../../shared/cn'
import { AGENT_META, ACTION_BADGE } from '../../../shared/theme'
import type { AgentState } from '../domain/types'

interface AgentSpriteProps {
  state: AgentState
  /** Show larger card (used for leslie's leader position) */
  isLeader?: boolean
}

export function AgentSprite({ state, isLeader = false }: AgentSpriteProps) {
  const meta = AGENT_META[state.id]
  const badge = ACTION_BADGE[state.action]

  const spriteSize = isLeader ? 'w-16 h-16' : 'w-12 h-12'
  const initialsSize = isLeader ? 'text-2xl' : 'text-lg'

  return (
    <div
      data-testid={`agent-${state.id}`}
      className={cn(
        'flex flex-col items-center gap-3',
        isLeader && 'items-center'
      )}
    >
      {/* Pixel-art avatar square */}
      <div
        className={cn(
          'pioneer-tooltip pixel-sprite relative flex items-center justify-center',
          'rounded-sm border-2 font-mono font-bold select-none',
          spriteSize,
          'transition-all duration-200'
        )}
        style={{
          backgroundColor: `${meta.color}22`,
          borderColor: meta.color,
          color: meta.color,
          boxShadow: state.action !== 'idle'
            ? `0 0 12px ${meta.color}55, inset 0 0 8px ${meta.color}22`
            : 'none',
        }}
        data-tooltip={meta.tooltip}
      >
        {/* Pixel scanlines overlay */}
        <span
          className={cn('absolute inset-0 rounded-sm opacity-20')}
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.3) 3px, rgba(0,0,0,0.3) 4px)',
          }}
          aria-hidden
        />

        {/* Initials */}
        <span className={cn(initialsSize, 'relative z-10 leading-none')}>
          {meta.name.slice(0, 2).toUpperCase()}
        </span>

        {/* Status indicator dot */}
        {state.action !== 'idle' && (
          <span
            className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full border border-slate-900"
            style={{ backgroundColor: meta.color }}
            aria-hidden
          />
        )}
      </div>

      {/* Agent info */}
      <div className="flex flex-col items-center gap-1 text-center">
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
        <span className="text-xs text-slate-500 font-mono uppercase tracking-widest">
          {meta.role}
        </span>

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
          <p className="text-xs text-slate-400 max-w-[120px] text-center leading-tight mt-1 line-clamp-2">
            {state.message}
          </p>
        )}
      </div>
    </div>
  )
}
