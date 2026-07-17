import { useCallback, useEffect, useRef, useState } from 'react'
import { useAgentMovement } from '../features/crew-office/application/useAgentMovement'
import { useCrewSession } from '../features/crew-office/application/useCrewSession'
import { createApiClient } from '../features/crew-office/infrastructure/apiClient'
import { createSseClientFactory } from '../features/crew-office/infrastructure/sseClient'
import { ChallengeDialog } from '../features/crew-office/ui/ChallengeDialog'
import { Office } from '../features/crew-office/ui/Office'
import { PlanDialog } from '../features/crew-office/ui/PlanDialog'
import type { AgentEvent } from '../features/crew-office/domain/types'
import { API_BASE_URL } from '../shared/config'

const apiClient = createApiClient(API_BASE_URL)
const sseClientFactory = createSseClientFactory()

function bubbleText(message: string): string {
  const compact = message.replace(/\s+/g, ' ').trim()
  return compact.length > 92 ? `${compact.slice(0, 89)}…` : compact
}

/** The HUB is the main UI: click Leslie to give the crew a real mission. */
export function App() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [planDialogOpen, setPlanDialogOpen] = useState(false)
  const presentedPlanSessionRef = useRef<string | null>(null)
  const {
    motions,
    clearThoughts,
    gatherAtMeeting,
    moveToStation,
    returnToMeeting,
    setThought,
  } = useAgentMovement()

  const handleAgentEvent = useCallback((event: AgentEvent) => {
    if (event.agent === 'leslie' && event.action === 'done') {
      clearThoughts()
    }
    setThought(event.agent, bubbleText(event.assignment ?? event.message))

    if (event.agent !== 'leslie' && event.action !== 'done') {
      void moveToStation(event.agent)
    }
  }, [clearThoughts, moveToStation, setThought])

  const { officeState, error, finalPlan, startSession } = useCrewSession({
    apiClient,
    sseClientFactory,
    onAgentEvent: handleAgentEvent,
  })

  const submitMission = useCallback((challenge: string) => {
    presentedPlanSessionRef.current = null
    setPlanDialogOpen(false)
    gatherAtMeeting()
    setThought('leslie', 'Analizando la misión…')
    setDialogOpen(false)
    void startSession(challenge)
  }, [gatherAtMeeting, setThought, startSession])

  useEffect(() => {
    if (!officeState.isDone || !officeState.sessionId || !finalPlan) return
    if (presentedPlanSessionRef.current === officeState.sessionId) return

    presentedPlanSessionRef.current = officeState.sessionId
    let cancelled = false

    void (async () => {
      clearThoughts()
      setThought('leslie', 'Crew, volvamos a la plaza…')
      await returnToMeeting()
      if (cancelled) return
      clearThoughts()
      setThought('leslie', 'Plan final listo.')
      setPlanDialogOpen(true)
    })()

    return () => {
      cancelled = true
    }
  }, [clearThoughts, finalPlan, officeState.isDone, officeState.sessionId, returnToMeeting, setThought])

  return (
    <main className="island-background" aria-label="Cloud Crew AI Hub">
      <Office
        officeState={officeState}
        motions={motions}
        onAgentSelect={() => {
          if (!officeState.isRunning) setDialogOpen(true)
        }}
      />
      <ChallengeDialog
        open={dialogOpen}
        isRunning={officeState.isRunning}
        error={error}
        onClose={() => setDialogOpen(false)}
        onSubmit={submitMission}
      />
      <PlanDialog
        open={planDialogOpen}
        plan={finalPlan}
        onClose={() => setPlanDialogOpen(false)}
      />
    </main>
  )
}
