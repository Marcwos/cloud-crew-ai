import type { CrewSession } from '../domain/types'

// ── Interface ──────────────────────────────────────────────────────────────

export interface ApiClient {
  createSession(challenge: string): Promise<{ session_id: string }>
  getSession(sessionId: string): Promise<CrewSession>
}

// ── Factory ────────────────────────────────────────────────────────────────

export function createApiClient(baseUrl: string): ApiClient {
  async function post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText)
      throw new Error(`POST ${path} failed (${response.status}): ${text}`)
    }

    return response.json() as Promise<T>
  }

  async function get<T>(path: string): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`)

    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText)
      throw new Error(`GET ${path} failed (${response.status}): ${text}`)
    }

    return response.json() as Promise<T>
  }

  return {
    createSession(challenge: string) {
      return post<{ session_id: string }>('/api/sessions', { challenge })
    },

    getSession(sessionId: string) {
      return get<CrewSession>(`/api/sessions/${sessionId}`)
    },
  }
}
