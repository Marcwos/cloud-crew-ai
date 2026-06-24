import type { AgentEvent } from '../domain/types'
import { parseAgentEvent } from '../application/agentEvent.parser'

// ── Interface ──────────────────────────────────────────────────────────────

export interface SseClientFactory {
  /**
   * Opens an SSE connection to `url`.
   * - onEvent is called for every `data:` line that parses as AgentEvent.
   * - onDone is called when the leslie/done terminal event fires.
   * - onError is called when the EventSource fires an error event.
   * - Returns a cleanup function that closes the connection.
   */
  create(
    url: string,
    onEvent: (event: AgentEvent) => void,
    onDone: () => void,
    onError: (message: string) => void
  ): () => void
}

// ── Factory ────────────────────────────────────────────────────────────────

export function createSseClientFactory(): SseClientFactory {
  return {
    create(url, onEvent, onDone, onError) {
      const source = new EventSource(url)

      source.onmessage = (ev: MessageEvent<string>) => {
        let parsed: AgentEvent

        try {
          parsed = parseAgentEvent(ev.data)
        } catch (err) {
          // Log and skip malformed events — never crash the stream
          console.warn('[sseClient] failed to parse event:', ev.data, err)
          return
        }

        onEvent(parsed)

        if (parsed.agent === 'leslie' && parsed.action === 'done') {
          source.close()
          onDone()
        }
      }

      source.onerror = (err) => {
        console.error('[sseClient] EventSource error:', err)
        source.close()
        onError('SSE connection lost')
      }

      // Return cleanup — callers can invoke this to abort early
      return () => {
        source.close()
      }
    },
  }
}
