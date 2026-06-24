import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCrewSession } from './useCrewSession'
import type { ApiClient } from '../infrastructure/apiClient'
import type { SseClientFactory } from '../infrastructure/sseClient'
import type { AgentEvent } from '../domain/types'

// ── Mock factories ─────────────────────────────────────────────────────────

function makeMockApiClient(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    createSession: vi.fn().mockResolvedValue({ session_id: 'test-session-id' }),
    getSession: vi.fn().mockResolvedValue({
      session_id: 'test-session-id',
      challenge: 'build an app',
      final_plan: {
        summary: 'Deploy on AWS',
        services: ['EC2', 'RDS'],
        justification_by_service: { EC2: 'compute', RDS: 'database' },
        diagram_hint: 'EC2 -> RDS',
      },
    }),
    ...overrides,
  }
}

function makeMockSseFactory(
  onCreateCallback?: (
    url: string,
    onEvent: (event: AgentEvent) => void,
    onDone: () => void,
    onError: (message: string) => void
  ) => void
): SseClientFactory {
  return {
    create: vi.fn().mockImplementation(
      (
        url: string,
        onEvent: (event: AgentEvent) => void,
        onDone: () => void,
        onError: (message: string) => void
      ) => {
        if (onCreateCallback) {
          onCreateCallback(url, onEvent, onDone, onError)
        }
        // Return a cleanup function
        return () => {}
      }
    ),
  }
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('useCrewSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initialises with idle office state', () => {
    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: makeMockSseFactory(),
      })
    )

    expect(result.current.officeState.isRunning).toBe(false)
    expect(result.current.officeState.isDone).toBe(false)
    expect(result.current.officeState.sessionId).toBeNull()
    expect(result.current.finalPlan).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('calls apiClient.createSession with the challenge text', async () => {
    const mockApi = makeMockApiClient()

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: mockApi,
        sseClientFactory: makeMockSseFactory(),
      })
    )

    await act(async () => {
      await result.current.startSession('design a microservice')
    })

    expect(mockApi.createSession).toHaveBeenCalledWith('design a microservice')
    expect(mockApi.createSession).toHaveBeenCalledTimes(1)
  })

  it('sets sessionId and isRunning after createSession resolves', async () => {
    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: makeMockSseFactory(),
      })
    )

    await act(async () => {
      await result.current.startSession('build a pipeline')
    })

    expect(result.current.officeState.sessionId).toBe('test-session-id')
    expect(result.current.officeState.isRunning).toBe(true)
  })

  it('opens SSE connection to the session events URL', async () => {
    const mockSseFactory = makeMockSseFactory()

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test challenge')
    })

    expect(mockSseFactory.create).toHaveBeenCalledTimes(1)
    const [url] = (mockSseFactory.create as ReturnType<typeof vi.fn>).mock.calls[0] as [string, unknown, unknown]
    expect(url).toContain('test-session-id')
    expect(url).toContain('events')
  })

  it('dispatches SSE events to update agent state', async () => {
    let capturedOnEvent: ((event: AgentEvent) => void) | null = null

    const mockSseFactory = makeMockSseFactory((_url, onEvent) => {
      capturedOnEvent = onEvent
    })

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test')
    })

    expect(capturedOnEvent).not.toBeNull()

    act(() => {
      capturedOnEvent!({
        agent: 'alan',
        action: 'analyzing',
        status: 'busy',
        message: 'Running',
      })
    })

    expect(result.current.officeState.agents['alan'].action).toBe('analyzing')
  })

  it('fetches the session and sets finalPlan when leslie/done fires', async () => {
    let capturedOnEvent: ((event: AgentEvent) => void) | null = null
    let capturedOnDone: (() => void) | null = null

    const mockApi = makeMockApiClient()
    const mockSseFactory = makeMockSseFactory((_url, onEvent, onDone) => {
      capturedOnEvent = onEvent
      capturedOnDone = onDone
    })

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: mockApi,
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test')
    })

    // 1. fire the leslie/done event (updates agent state + sets isDone in reducer)
    act(() => {
      capturedOnEvent!({
        agent: 'leslie',
        action: 'done',
        status: 'finished',
        message: 'All done',
      })
    })

    // 2. call onDone (simulates what the real SSE client does after detecting leslie/done)
    await act(async () => {
      capturedOnDone!()
      // Let the async getSession promise resolve
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    expect(mockApi.getSession).toHaveBeenCalledWith('test-session-id')
    expect(result.current.finalPlan).not.toBeNull()
    expect(result.current.finalPlan?.summary).toBe('Deploy on AWS')
    expect(result.current.officeState.isDone).toBe(true)
  })

  it('sets error state when createSession fails', async () => {
    const mockApi = makeMockApiClient({
      createSession: vi.fn().mockRejectedValue(new Error('Network error')),
    })

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: mockApi,
        sseClientFactory: makeMockSseFactory(),
      })
    )

    await act(async () => {
      await result.current.startSession('test challenge')
    })

    expect(result.current.error).not.toBeNull()
    expect(result.current.error).toContain('Network error')
  })

  it('sets error state when getSession fails after leslie/done', async () => {
    let capturedOnDone: (() => void) | null = null

    const mockApi = makeMockApiClient({
      getSession: vi.fn().mockRejectedValue(new Error('Fetch failed')),
    })
    const mockSseFactory = makeMockSseFactory((_url, _onEvent, onDone) => {
      capturedOnDone = onDone
    })

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: mockApi,
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test')
    })

    await act(async () => {
      capturedOnDone!()
      await new Promise(resolve => setTimeout(resolve, 10))
    })

    expect(result.current.error).not.toBeNull()
  })

  // ── BLOCKER 1: SSE cleanup on unmount ─────────────────────────────────────

  it('calls the SSE cleanup function when the hook unmounts mid-stream', async () => {
    const cleanup = vi.fn()
    const mockSseFactory: SseClientFactory = {
      create: vi.fn().mockImplementation(() => cleanup),
    }

    const { result, unmount } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test')
    })

    expect(cleanup).not.toHaveBeenCalled()

    // Unmount mid-stream — cleanup must fire
    unmount()

    expect(cleanup).toHaveBeenCalledTimes(1)
  })

  // ── BLOCKER 2: SSE error surfaces to UI and clears running state ──────────

  it('sets error and clears isRunning when the SSE stream errors', async () => {
    let capturedOnError: ((message: string) => void) | null = null

    const mockSseFactory = makeMockSseFactory((_url, _onEvent, _onDone, onError) => {
      capturedOnError = onError
    })

    const { result } = renderHook(() =>
      useCrewSession({
        apiClient: makeMockApiClient(),
        sseClientFactory: mockSseFactory,
      })
    )

    await act(async () => {
      await result.current.startSession('test')
    })

    expect(result.current.officeState.isRunning).toBe(true)
    expect(capturedOnError).not.toBeNull()

    act(() => {
      capturedOnError!('Connection lost')
    })

    expect(result.current.officeState.isRunning).toBe(false)
    expect(result.current.error).toBe('Connection lost')
  })
})
