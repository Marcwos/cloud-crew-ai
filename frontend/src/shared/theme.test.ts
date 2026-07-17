import { describe, it, expect } from 'vitest'
import { agentFloorPosition, HOME_POS, MEETING_POS } from './theme'

describe('agentFloorPosition', () => {
  it('sits at the desk when idle', () => {
    expect(agentFloorPosition('alan', 'idle')).toEqual(HOME_POS.alan)
  })

  it('returns to the desk when done', () => {
    expect(agentFloorPosition('alan', 'done')).toEqual(HOME_POS.alan)
  })

  it('gathers at the table when active', () => {
    for (const action of ['moving', 'analyzing', 'proposing', 'reviewing'] as const) {
      expect(agentFloorPosition('alan', action)).toEqual(MEETING_POS.alan)
    }
  })
})
