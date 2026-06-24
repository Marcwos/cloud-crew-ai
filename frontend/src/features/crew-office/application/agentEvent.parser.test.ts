import { describe, it, expect } from 'vitest'
import { parseAgentEvent } from './agentEvent.parser'

describe('parseAgentEvent', () => {
  it('parses a valid SSE data string into an AgentEvent', () => {
    const data = JSON.stringify({
      agent: 'alan',
      action: 'analyzing',
      status: 'working',
      message: 'Processing data',
    })

    const event = parseAgentEvent(data)

    expect(event.agent).toBe('alan')
    expect(event.action).toBe('analyzing')
    expect(event.status).toBe('working')
    expect(event.message).toBe('Processing data')
  })

  it('throws when the data is not valid JSON', () => {
    expect(() => parseAgentEvent('not json at all')).toThrow()
  })

  it('throws when required field "agent" is missing', () => {
    const data = JSON.stringify({
      action: 'analyzing',
      status: 'working',
      message: 'hello',
    })
    expect(() => parseAgentEvent(data)).toThrow(/agent/)
  })

  it('throws when required field "action" is missing', () => {
    const data = JSON.stringify({
      agent: 'alan',
      status: 'working',
      message: 'hello',
    })
    expect(() => parseAgentEvent(data)).toThrow(/action/)
  })

  it('throws when "agent" is not a valid AgentId', () => {
    const data = JSON.stringify({
      agent: 'hal9000',
      action: 'analyzing',
      status: '',
      message: '',
    })
    expect(() => parseAgentEvent(data)).toThrow(/agent/)
  })

  it('throws when "action" is not a valid AgentAction', () => {
    const data = JSON.stringify({
      agent: 'leslie',
      action: 'plotting-world-domination',
      status: '',
      message: '',
    })
    expect(() => parseAgentEvent(data)).toThrow(/action/)
  })

  it('ignores unknown extra fields and still parses successfully', () => {
    const data = JSON.stringify({
      agent: 'vint',
      action: 'moving',
      status: 'routing',
      message: 'Setting up network',
      someRandomExtra: 42,
      anotherExtra: { nested: true },
    })

    const event = parseAgentEvent(data)

    expect(event.agent).toBe('vint')
    expect(event.action).toBe('moving')
    // extra fields should not be on the returned object
    expect((event as unknown as Record<string, unknown>)['someRandomExtra']).toBeUndefined()
  })

  it('handles empty status and message gracefully', () => {
    const data = JSON.stringify({
      agent: 'hedy',
      action: 'idle',
      status: '',
      message: '',
    })

    const event = parseAgentEvent(data)

    expect(event.agent).toBe('hedy')
    expect(event.status).toBe('')
    expect(event.message).toBe('')
  })

  it('parses all six valid agent ids without throwing', () => {
    const agentIds = ['leslie', 'alan', 'edgar', 'hedy', 'grace', 'vint'] as const
    for (const agent of agentIds) {
      const data = JSON.stringify({ agent, action: 'idle', status: '', message: '' })
      expect(() => parseAgentEvent(data)).not.toThrow()
    }
  })

  it('parses all six valid actions without throwing', () => {
    const actions = ['idle', 'moving', 'analyzing', 'proposing', 'reviewing', 'done'] as const
    for (const action of actions) {
      const data = JSON.stringify({ agent: 'leslie', action, status: '', message: '' })
      expect(() => parseAgentEvent(data)).not.toThrow()
    }
  })
})
