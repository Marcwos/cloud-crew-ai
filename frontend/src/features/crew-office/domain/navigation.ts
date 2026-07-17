import type { AgentId } from './types'

export interface MapPoint {
  x: number
  y: number
}

export interface Waypoint extends MapPoint {
  id: string
  connections: readonly string[]
}

/**
 * Navigation graph for the fixed HUB artwork. Points are deliberately placed
 * on the visible paths, never through buildings or workstations.
 */
export const WAYPOINTS: Record<string, Waypoint> = {
  plaza: { id: 'plaza', x: 50, y: 66, connections: ['north', 'west', 'east', 'south'] },
  north: { id: 'north', x: 50, y: 57, connections: ['plaza', 'leslie'] },
  west: { id: 'west', x: 38, y: 64, connections: ['plaza', 'alan', 'hedy'] },
  east: { id: 'east', x: 62, y: 64, connections: ['plaza', 'edgar', 'grace'] },
  south: { id: 'south', x: 50, y: 78, connections: ['plaza', 'vint'] },
  leslie: { id: 'leslie', x: 50, y: 48, connections: ['north'] },
  alan: { id: 'alan', x: 30, y: 47, connections: ['west'] },
  edgar: { id: 'edgar', x: 70, y: 47, connections: ['east'] },
  hedy: { id: 'hedy', x: 28, y: 71, connections: ['west'] },
  grace: { id: 'grace', x: 72, y: 71, connections: ['east'] },
  vint: { id: 'vint', x: 50, y: 86, connections: ['south'] },
}

export const STATION_WAYPOINT: Record<AgentId, string> = {
  leslie: 'leslie',
  alan: 'alan',
  edgar: 'edgar',
  hedy: 'hedy',
  grace: 'grace',
  vint: 'vint',
}

/** Breadth-first search over the small, unweighted navigation graph. */
export function findRoute(from: string, to: string): Waypoint[] {
  const start = WAYPOINTS[from]
  const end = WAYPOINTS[to]
  if (!start || !end) return []
  if (from === to) return [start]

  const queue = [from]
  const previous = new Map<string, string>()
  const visited = new Set([from])

  while (queue.length > 0) {
    const current = queue.shift()!
    const currentWaypoint = WAYPOINTS[current]
    if (!currentWaypoint) continue
    for (const next of currentWaypoint.connections) {
      if (visited.has(next)) continue
      visited.add(next)
      previous.set(next, current)
      if (next === to) {
        const path = [to]
        let cursor = to
        while (previous.has(cursor)) {
          cursor = previous.get(cursor)!
          path.unshift(cursor)
        }
        return path.reduce<Waypoint[]>((points, id) => {
          const point = WAYPOINTS[id]
          if (point) points.push(point)
          return points
        }, [])
      }
      queue.push(next)
    }
  }

  return []
}
