import { useState, useRef } from 'react'
import { cn } from '../../../shared/cn'

interface ChallengeInputProps {
  onSubmit: (challenge: string) => void
  isRunning: boolean
  isDone: boolean
}

export function ChallengeInput({ onSubmit, isRunning, isDone }: ChallengeInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || isRunning) return
    onSubmit(trimmed)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  const buttonLabel = isRunning
    ? 'Crew Working…'
    : isDone
      ? 'Run Again'
      : 'Deploy Crew'

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-slate-700 bg-slate-900/80 p-5 flex flex-col gap-4 backdrop-blur-sm"
      style={{
        boxShadow: '0 0 0 1px rgba(139,92,246,0.1), 0 4px 32px rgba(0,0,0,0.4)',
      }}
    >
      {/* Label */}
      <label
        htmlFor="challenge-textarea"
        className="text-xs font-mono text-slate-500 uppercase tracking-widest"
      >
        // challenge.input
      </label>

      {/* Textarea */}
      <div
        className={cn(
          'rounded border px-4 py-3 transition-colors duration-150',
          'border-slate-700 focus-within:border-cyan-500/60',
          'bg-slate-950/60'
        )}
        style={{
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)',
        }}
      >
        <textarea
          id="challenge-textarea"
          ref={textareaRef}
          data-testid="challenge-input"
          className="challenge-textarea min-h-[100px]"
          placeholder="Describe the cloud infrastructure challenge for the crew…&#10;&#10;e.g. Design a multi-region microservices platform with auto-scaling,&#10;     observability, and zero-trust security."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
          rows={5}
          aria-label="Challenge description"
        />
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between gap-4">
        <span className="text-xs text-slate-600 font-mono">
          {isRunning ? (
            <span className="text-cyan-500 badge-analyzing inline-block">
              ● crew active
            </span>
          ) : (
            <span>⌘+Enter to submit</span>
          )}
        </span>

        <button
          data-testid="submit-challenge"
          type="submit"
          disabled={isRunning || !value.trim()}
          className={cn(
            'px-5 py-2 rounded font-mono text-sm font-semibold',
            'transition-all duration-150',
            'border',
            isRunning
              ? 'border-slate-700 bg-slate-800 text-slate-500 cursor-not-allowed'
              : isDone
                ? 'border-emerald-600 bg-emerald-900/50 text-emerald-300 hover:bg-emerald-900/80'
                : 'border-violet-600 bg-violet-900/50 text-violet-200 hover:bg-violet-800/60 hover:border-violet-500',
            !value.trim() && !isRunning && 'opacity-50'
          )}
        >
          {buttonLabel}
        </button>
      </div>
    </form>
  )
}
