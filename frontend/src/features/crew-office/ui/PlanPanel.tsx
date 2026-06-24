import { cn } from '../../../shared/cn'
import type { FinalPlan } from '../domain/types'

interface PlanPanelProps {
  plan: FinalPlan
}

// Simple palette cycling for service items
const SERVICE_COLORS = [
  { border: '#8B5CF6', text: '#C4B5FD', bg: '#8B5CF611' },
  { border: '#3B82F6', text: '#93C5FD', bg: '#3B82F611' },
  { border: '#10B981', text: '#6EE7B7', bg: '#10B98111' },
  { border: '#F59E0B', text: '#FCD34D', bg: '#F59E0B11' },
  { border: '#EF4444', text: '#FCA5A5', bg: '#EF444411' },
  { border: '#06B6D4', text: '#67E8F9', bg: '#06B6D411' },
]

export function PlanPanel({ plan }: PlanPanelProps) {
  return (
    <div
      data-testid="plan-panel"
      className="plan-panel"
    >
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-700 flex items-center gap-3">
        <span className="text-emerald-400 font-mono text-sm">✓</span>
        <span className="font-mono text-xs text-slate-400 uppercase tracking-widest">
          crew.output — final_plan
        </span>
        <span className="ml-auto text-xs text-emerald-500 font-mono badge-analyzing inline-block">
          ready
        </span>
      </div>

      <div className="p-5 flex flex-col gap-6">
        {/* Summary */}
        <section>
          <h3 className="font-mono text-xs text-slate-500 uppercase tracking-widest mb-2">
            // summary
          </h3>
          <p className="text-slate-200 text-sm leading-relaxed">
            {plan.summary}
          </p>
        </section>

        {/* Diagram hint */}
        {plan.diagram_hint && (
          <section>
            <h3 className="font-mono text-xs text-slate-500 uppercase tracking-widest mb-2">
              // architecture_hint
            </h3>
            <pre
              className={cn(
                'text-xs text-cyan-300 font-mono',
                'bg-slate-950/60 rounded border border-slate-700/50',
                'px-4 py-3 overflow-x-auto leading-relaxed whitespace-pre-wrap'
              )}
            >
              {plan.diagram_hint}
            </pre>
          </section>
        )}

        {/* Services + justifications */}
        {plan.services.length > 0 && (
          <section>
            <h3 className="font-mono text-xs text-slate-500 uppercase tracking-widest mb-3">
              // services [{plan.services.length}]
            </h3>
            <div className="flex flex-col gap-3">
              {plan.services.map((service, idx) => {
                const palette = SERVICE_COLORS[idx % SERVICE_COLORS.length]!
                const justification = plan.justification_by_service[service]

                return (
                  <div
                    key={service}
                    className="plan-service-item"
                    style={{
                      borderColor: palette.border,
                      backgroundColor: palette.bg,
                    }}
                  >
                    <div className="flex items-start gap-3">
                      {/* Service tag */}
                      <span
                        className="font-mono text-xs font-bold px-2 py-0.5 rounded shrink-0 mt-0.5"
                        style={{
                          color: palette.text,
                          backgroundColor: `${palette.border}22`,
                          border: `1px solid ${palette.border}55`,
                        }}
                      >
                        {service}
                      </span>

                      {/* Justification */}
                      {justification && (
                        <p className="text-sm text-slate-300 leading-relaxed">
                          {justification}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
