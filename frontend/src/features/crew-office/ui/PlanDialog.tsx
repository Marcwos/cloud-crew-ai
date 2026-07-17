import type { FinalPlan } from '../domain/types'

interface PlanDialogProps {
  open: boolean
  plan: FinalPlan | null
  onClose: () => void
}

/** Final debrief shown once the crew has returned to the central plaza. */
export function PlanDialog({ open, plan, onClose }: PlanDialogProps) {
  if (!open || !plan) return null

  return (
    <div className="challenge-dialog-backdrop" role="presentation">
      <section
        className="challenge-dialog plan-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Crew proposed plan"
      >
        <button
          type="button"
          className="challenge-dialog-close"
          onClick={onClose}
          aria-label="Close proposed plan"
        >
          ×
        </button>
        <p className="challenge-dialog-kicker">CREW · PROPUESTA FINAL</p>
        <h1>Plan de arquitectura</h1>
        <p className="plan-dialog-summary">{plan.summary}</p>

        <h2>Servicios propuestos</h2>
        <ul className="plan-dialog-services">
          {plan.services.map((service) => (
            <li key={service}>
              <strong>{service}</strong>
              {plan.justification_by_service[service] && (
                <span>{plan.justification_by_service[service]}</span>
              )}
            </li>
          ))}
        </ul>

        {plan.diagram_hint && (
          <p className="plan-dialog-hint">
            <span>Flujo:</span> {plan.diagram_hint}
          </p>
        )}
      </section>
    </div>
  )
}
