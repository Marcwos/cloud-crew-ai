import { useMemo } from 'react'
import { useCrewSession } from '../features/crew-office/application/useCrewSession'
import { createApiClient } from '../features/crew-office/infrastructure/apiClient'
import { createSseClientFactory } from '../features/crew-office/infrastructure/sseClient'
import { Office } from '../features/crew-office/ui/Office'
import { ChallengeInput } from '../features/crew-office/ui/ChallengeInput'
import { PlanPanel } from '../features/crew-office/ui/PlanPanel'
import { API_BASE_URL } from '../shared/config'

export function App() {
  // Stable dependency instances (only created once per mount)
  const apiClient = useMemo(() => createApiClient(API_BASE_URL), [])
  const sseClientFactory = useMemo(() => createSseClientFactory(), [])

  const { officeState, finalPlan, error, startSession } = useCrewSession({
    apiClient,
    sseClientFactory,
  })

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
        <div className="flex items-center gap-3">
          {/* Pixel logo */}
          <div
            className="w-8 h-8 rounded-sm flex items-center justify-center font-mono text-sm font-bold text-white"
            style={{
              background: 'linear-gradient(135deg, #8B5CF6 0%, #3B82F6 100%)',
              imageRendering: 'pixelated',
            }}
            aria-hidden
          >
            CC
          </div>
          <div>
            <h1 className="font-mono text-sm font-bold text-slate-100 leading-none">
              Cloud Crew AI
            </h1>
            <p className="font-mono text-xs text-slate-500 leading-none mt-0.5">
              pixel office — v0.1
            </p>
          </div>
        </div>

        {/* Status pill */}
        <div className="ml-auto flex items-center gap-2">
          {officeState.isRunning && (
            <span className="flex items-center gap-1.5 text-xs font-mono text-cyan-400 badge-analyzing">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 inline-block" />
              crew active
            </span>
          )}
          {officeState.isDone && (
            <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              mission complete
            </span>
          )}
          {!officeState.isRunning && !officeState.isDone && (
            <span className="flex items-center gap-1.5 text-xs font-mono text-slate-600">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
              standby
            </span>
          )}
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="flex-1 px-4 py-8 max-w-5xl mx-auto w-full flex flex-col gap-8">
        {/* Error banner */}
        {error && (
          <div
            role="alert"
            className="rounded border border-red-800 bg-red-950/50 px-4 py-3 font-mono text-sm text-red-400"
          >
            <span className="font-bold">error:</span> {error}
          </div>
        )}

        {/* Challenge input */}
        <ChallengeInput
          onSubmit={startSession}
          isRunning={officeState.isRunning}
          isDone={officeState.isDone}
        />

        {/* Office */}
        <Office officeState={officeState} />

        {/* Final plan */}
        {finalPlan && <PlanPanel plan={finalPlan} />}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800 px-6 py-3 text-center">
        <span className="font-mono text-xs text-slate-700">
          cloud crew ai — built with react 19 + vite + tailwind 4
        </span>
      </footer>
    </div>
  )
}
