import { useCallback, useEffect, useRef, useState } from 'react'
import { AGENT_IDS, type AgentId } from '../domain/types'
import {
  findRoute,
  STATION_WAYPOINT,
  WAYPOINTS,
  type MapPoint,
} from '../domain/navigation'

export interface AgentMotion extends MapPoint {
  isWalking: boolean
  thought: string | null
}

type MotionByAgent = Record<AgentId, AgentMotion>

const ASSIGNMENT_MEETING_POSITIONS: Record<AgentId, MapPoint> = {
  leslie: WAYPOINTS.leslie!,
  alan: { x: 44, y: 62 },
  edgar: { x: 56, y: 62 },
  hedy: { x: 43, y: 70 },
  grace: { x: 57, y: 70 },
  vint: { x: 50, y: 76 },
}

const FINAL_MEETING_POSITIONS: Record<AgentId, MapPoint> = {
  leslie: { x: 50, y: 60 },
  alan: { x: 43, y: 65 },
  edgar: { x: 57, y: 65 },
  hedy: { x: 43, y: 72 },
  grace: { x: 57, y: 72 },
  vint: { x: 50, y: 77 },
}

const WALK_SPEED = 18 // map percentage points per second

function createStationMotions(): MotionByAgent {
  return Object.fromEntries(
    AGENT_IDS.map((id) => {
      const station = WAYPOINTS[STATION_WAYPOINT[id]]!
      return [id, { x: station.x, y: station.y, isWalking: false, thought: null }]
    })
  ) as MotionByAgent
}

/**
 * Moves lightweight avatar placeholders through the navigation graph. The
 * same API will work with directional spritesheets once those assets exist.
 */
export function useAgentMovement() {
  const [motions, setMotions] = useState<MotionByAgent>(createStationMotions)
  const motionsRef = useRef(motions)
  const nodeRef = useRef<Record<AgentId, string>>(
    Object.fromEntries(AGENT_IDS.map((id) => [id, STATION_WAYPOINT[id]])) as Record<AgentId, string>
  )
  const frameRef = useRef<number | null>(null)
  const cancelledRef = useRef(false)
  const queuesRef = useRef<Record<AgentId, Promise<void>>>(
    Object.fromEntries(AGENT_IDS.map((id) => [id, Promise.resolve()])) as Record<AgentId, Promise<void>>
  )

  const updateMotion = useCallback((agent: AgentId, patch: Partial<AgentMotion>) => {
    setMotions((current) => {
      const next = { ...current, [agent]: { ...current[agent], ...patch } }
      motionsRef.current = next
      return next
    })
  }, [])

  const travel = useCallback(async (agent: AgentId, destination: string) => {
    const route = findRoute(nodeRef.current[agent], destination)
    if (route.length === 0 || route.length === 1) return

    updateMotion(agent, { isWalking: true })
    for (const target of route.slice(1)) {
      const start = motionsRef.current[agent]
      const distance = Math.hypot(target.x - start.x, target.y - start.y)
      const duration = Math.max(280, (distance / WALK_SPEED) * 1000)

      await new Promise<void>((resolve) => {
        const startedAt = performance.now()
        const tick = (now: number) => {
          if (cancelledRef.current) return resolve()
          const progress = Math.min(1, (now - startedAt) / duration)
          const eased = progress * (2 - progress)
          updateMotion(agent, {
            x: start.x + (target.x - start.x) * eased,
            y: start.y + (target.y - start.y) * eased,
          })
          if (progress < 1) {
            frameRef.current = requestAnimationFrame(tick)
          } else {
            resolve()
          }
        }
        frameRef.current = requestAnimationFrame(tick)
      })
    }

    nodeRef.current[agent] = destination
    updateMotion(agent, { isWalking: false })
  }, [updateMotion])

  const moveAgent = useCallback((agent: AgentId, destination: string) => {
    const queued = queuesRef.current[agent]
      .catch(() => undefined)
      .then(() => travel(agent, destination))
    queuesRef.current[agent] = queued
    return queued
  }, [travel])

  const moveToStation = useCallback((agent: AgentId) => (
    moveAgent(agent, STATION_WAYPOINT[agent])
  ), [moveAgent])

  const setThought = useCallback((agent: AgentId, thought: string | null) => {
    updateMotion(agent, { thought })
  }, [updateMotion])

  const clearThoughts = useCallback(() => {
    setMotions((current) => {
      const next = Object.fromEntries(
        AGENT_IDS.map((id) => [id, { ...current[id], thought: null }])
      ) as MotionByAgent
      motionsRef.current = next
      return next
    })
  }, [])

  const gatherAtMeeting = useCallback(() => {
    const gathered = Object.fromEntries(
      AGENT_IDS.map((id) => [id, { ...ASSIGNMENT_MEETING_POSITIONS[id], isWalking: false, thought: null }])
    ) as MotionByAgent
    motionsRef.current = gathered
    setMotions(gathered)
    nodeRef.current = Object.fromEntries(
      AGENT_IDS.map((id) => [id, id === 'leslie' ? 'leslie' : 'plaza'])
    ) as Record<AgentId, string>
    queuesRef.current = Object.fromEntries(
      AGENT_IDS.map((id) => [id, Promise.resolve()])
    ) as Record<AgentId, Promise<void>>
  }, [])

  /** Bring the whole crew back through the path network before the debrief. */
  const returnToMeeting = useCallback(async () => {
    await Promise.all(AGENT_IDS.map((id) => moveAgent(id, 'plaza')))

    const gathered = Object.fromEntries(
      AGENT_IDS.map((id) => [id, { ...FINAL_MEETING_POSITIONS[id], isWalking: false, thought: null }])
    ) as MotionByAgent
    motionsRef.current = gathered
    setMotions(gathered)
    nodeRef.current = Object.fromEntries(
      AGENT_IDS.map((id) => [id, 'plaza'])
    ) as Record<AgentId, string>
  }, [moveAgent])

  useEffect(() => {
    cancelledRef.current = false
    return () => {
      cancelledRef.current = true
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    }
  }, [])

  return {
    motions,
    clearThoughts,
    gatherAtMeeting,
    moveToStation,
    returnToMeeting,
    setThought,
  }
}
