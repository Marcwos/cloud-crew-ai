import { describe, expect, it } from 'vitest'
import { findRoute } from './navigation'

describe('findRoute', () => {
  it('routes Alan through the path network from the central plaza', () => {
    expect(findRoute('plaza', 'alan').map((point) => point.id)).toEqual([
      'plaza',
      'west',
      'alan',
    ])
  })

  it('returns no route for unknown points', () => {
    expect(findRoute('unknown', 'alan')).toEqual([])
  })
})
