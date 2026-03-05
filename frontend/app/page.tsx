'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { submitTask } from '@/lib/api';

const EXAMPLES = [
  'Research the pros and cons of microservices vs. monoliths and produce a summary report.',
  'Analyze the impact of large language models on software engineering workflows.',
  'Compare REST vs GraphQL API design approaches with practical recommendations.',
  'Investigate the current state of edge computing and its implications for web development.',
];

const AGENTS = [
  { icon: '🗺', label: 'Planner',    desc: 'Decomposes your request into ordered sub-tasks' },
  { icon: '🔬', label: 'Researcher', desc: 'Gathers findings for each sub-task concurrently' },
  { icon: '✍️', label: 'Writer',     desc: 'Synthesizes all research into a draft report' },
  { icon: '🔍', label: 'Reviewer',   desc: 'Scores quality and requests targeted revisions' },
];

export default function HomePage() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  async function handleSubmit() {
    if (!prompt.trim() || prompt.length < 10) return;
    setLoading(true);
    setError('');
    try {
      const { task_id } = await submitTask(prompt.trim());
      router.push(`/tasks/${task_id}`);
    } catch (e: any) {
      setError('Failed to submit task. Is the backend running?');
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-up" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4rem', paddingTop: '2rem', paddingBottom: '5rem' }}>

      {/* ── Hero ── */}
      <div className="animate-fade-up" style={{ textAlign: 'center', maxWidth: '640px' }}>
        {/* Pill badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          background: 'rgba(37,99,235,0.1)', border: '1px solid rgba(96,165,250,0.2)',
          borderRadius: '999px', padding: '6px 16px', marginBottom: '24px',
        }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--blue-bright)', display: 'inline-block', animation: 'pulse-ring 1.8s ease infinite' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--blue-bright)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Multi-Agent Orchestration
          </span>
        </div>

        <h1 className="animate-fade-up delay-100" style={{
          fontFamily: 'var(--font-syne)', fontSize: 'clamp(2.2rem, 5vw, 3.2rem)',
          fontWeight: 800, lineHeight: 1.1, color: 'var(--text-primary)', marginBottom: '1rem',
        }}>
          Four agents.<br />
          <span className="shimmer-text">One cohesive answer.</span>
        </h1>

        <p className="animate-fade-up delay-200" style={{
          color: 'var(--text-secondary)', fontSize: '1.05rem', lineHeight: 1.7, maxWidth: '520px', margin: '0 auto',
        }}>
          Submit a complex research request. Watch the Planner, Researcher, Writer,
          and Reviewer collaborate in real time to deliver a polished report.
        </p>
      </div>

      {/* ── Submission Card ── */}
      <div className="glass-elevated animate-fade-up delay-300" style={{ width: '100%', maxWidth: '640px', padding: '28px' }}>
        <label style={{
          display: 'block', fontSize: '0.8rem', fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '12px',
        }}>
          Your research request
        </label>

        <textarea
          className="input-field"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && e.metaKey && handleSubmit()}
          rows={4}
          placeholder="e.g. Research the pros and cons of microservices vs. monoliths..."
        />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {prompt.length} / 2000 · ⌘↵ to submit
          </span>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || prompt.trim().length < 10}
          >
            {loading ? (
              <>
                <span style={{
                  width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                  animation: 'spin 0.7s linear infinite',
                }} />
                Submitting…
              </>
            ) : (
              <>Launch Pipeline →</>
            )}
          </button>
        </div>

        {error && (
          <p style={{ color: 'var(--red)', fontSize: '0.78rem', marginTop: '8px', fontFamily: 'var(--font-mono)' }}>
            ⚠ {error}
          </p>
        )}
      </div>

      {/* ── Example Prompts ── */}
      <div className="animate-fade-up delay-400" style={{ width: '100%', maxWidth: '640px' }}>
        <p style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.12em', textAlign: 'center', marginBottom: '12px',
        }}>
          Try an example
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex)}
              style={{
                textAlign: 'left', fontSize: '0.85rem', color: 'var(--text-secondary)',
                background: 'rgba(13,20,32,0.5)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)', padding: '12px 16px',
                cursor: 'pointer', transition: 'all 0.2s var(--ease-out-expo)',
                fontFamily: 'var(--font-syne)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--border-glow)';
                e.currentTarget.style.color = 'var(--text-primary)';
                e.currentTarget.style.background = 'rgba(96,165,250,0.04)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.color = 'var(--text-secondary)';
                e.currentTarget.style.background = 'rgba(13,20,32,0.5)';
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* ── Agent Cards ── */}
      <div className="animate-fade-up delay-500" style={{
        width: '100%', maxWidth: '760px',
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px',
      }}>
        {AGENTS.map((agent, i) => (
          <div
            key={agent.label}
            className="glass"
            style={{ padding: '20px 16px', textAlign: 'center', animationDelay: `${0.5 + i * 0.08}s` }}
          >
            <div style={{ fontSize: '2rem', marginBottom: '10px' }}>{agent.icon}</div>
            <p style={{ fontFamily: 'var(--font-syne)', fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.9rem', marginBottom: '6px' }}>
              {agent.label}
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', lineHeight: 1.5 }}>
              {agent.desc}
            </p>
          </div>
        ))}
      </div>

      {/* Spin keyframe for loading button */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}