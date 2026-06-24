import { describe, it, expect } from 'vitest'
import { agentReducer, createInitialOfficeState } from './agentReducer'
import type { AgentEvent, OfficeState } from '../domain/types'

describe('agentReducer', () => {
  function makeState(): OfficeState {
    return createInitialOfficeState()
  }

  it('updates the targeted agent action on a normal event', () => {
    const state = makeState()
    const event: AgentEvent = {
      agent: 'alan',
      action: 'analyzing',
      status: 'working',
      message: 'Running compute analysis',
    }

    const next = agentReducer(state, event)

    expect(next.agents['alan'].action).toBe('analyzing')
    expect(next.agents['alan'].status).toBe('working')
    expect(next.agents['alan'].message).toBe('Running compute analysis')
  })

  it('leaves all other agents unchanged when only one agent fires', () => {
    const state = makeState()
    const event: AgentEvent = {
      agent: 'alan',
      action: 'analyzing',
      status: 'working',
      message: 'Running compute analysis',
    }

    const next = agentReducer(state, event)

    // Every agent except 'alan' must be untouched
    const others = (['leslie', 'edgar', 'hedy', 'grace', 'vint'] as const)
    for (const id of others) {
      expect(next.agents[id]).toEqual(state.agents[id])
    }
  })

  it('sets isDone=true and isRunning=false when leslie fires done', () => {
    const runningState: OfficeState = {
      ...makeState(),
      isRunning: true,
      isDone: false,
    }
    const event: AgentEvent = {
      agent: 'leslie',
      action: 'done',
      status: 'finished',
      message: 'All done',
    }

    const next = agentReducer(runningState, event)

    expect(next.isDone).toBe(true)
    expect(next.isRunning).toBe(false)
  })

  it('does not set isDone when a non-leslie agent fires done', () => {
    const state = makeState()
    const event: AgentEvent = {
      agent: 'alan',
      action: 'done',
      status: 'finished',
      message: 'Compute done',
    }

    const next = agentReducer(state, event)

    expect(next.isDone).toBe(false)
  })

  it('returns state unchanged for an unknown agent id', () => {
    const state = makeState()
    // Cast to AgentEvent to simulate a bad payload at runtime
    const event = {
      agent: 'unknown-bot' as never,
      action: 'analyzing' as const,
      status: '',
      message: '',
    } satisfies AgentEvent

    const next = agentReducer(state, event)

    expect(next).toEqual(state)
  })

  it('is idempotent: applying the same event twice yields the same result', () => {
    const state = makeState()
    const event: AgentEvent = {
      agent: 'edgar',
      action: 'proposing',
      status: 'draft',
      message: 'Building schema',
    }

    const once = agentReducer(state, event)
    const twice = agentReducer(once, event)

    expect(twice).toEqual(once)
  })

  it('never mutates the input state', () => {
    const state = makeState()
    const frozen = Object.freeze({
      ...state,
      agents: Object.freeze({
        ...state.agents,
        leslie: Object.freeze({ ...state.agents['leslie'] }),
        alan: Object.freeze({ ...state.agents['alan'] }),
        edgar: Object.freeze({ ...state.agents['edgar'] }),
        hedy: Object.freeze({ ...state.agents['hedy'] }),
        grace: Object.freeze({ ...state.agents['grace'] }),
        vint: Object.freeze({ ...state.agents['vint'] }),
      }),
    })

    const event: AgentEvent = {
      agent: 'grace',
      action: 'reviewing',
      status: 'costing',
      message: 'Checking costs',
    }

    expect(() => agentReducer(frozen, event)).not.toThrow()
  })
})
