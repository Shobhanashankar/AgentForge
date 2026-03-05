'use client';
import { useEffect, useRef, useState } from 'react';
import { getTask, createTaskSocket } from '@/lib/api';
import { Task, TaskStatus } from '@/lib/types';
import PipelineViz from '@/components/pipeline/PipelineViz';
import AgentLog from '@/components/pipeline/AgentLog';
import ReportViewer from '@/components/pipeline/ReportViewer';
import StatusBadge from '@/components/ui/StatusBadge';

type Tab = 'report' | 'log' | 'raw';

interface WaveTask { id: string; title: string; }
interface Wave { wave_index: number; tasks: WaveTask[]; }
interface SubtaskResult { task_id: string; task_title: string; confidence?: number; }

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [task, setTask]               = useState<Task | null>(null);
  const [activeTab, setActiveTab]     = useState<Tab>('log');
  const [error, setError]             = useState('');
  const [waves, setWaves]             = useState<Wave[]>([]);
  const [activeWave, setActiveWave]   = useState<number | null>(null);
  const [doneTaskIds, setDoneTaskIds] = useState<Set<string>>(new Set());
  const socketRef = useRef<WebSocket | null>(null);
  const pollRef   = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getTask(id).then(t => {
      setTask(t);
      // Restore wave data if task already has results (e.g. page refresh)
      if (t?.result?.waves) setWaves(t.result.waves);
    }).catch(() => setError('Task not found.'));

    const ws = createTaskSocket(id, (event) => {
      getTask(id).then(setTask).catch(() => {});

      // Handle wave-specific events
      if (event.type === 'WAVES_COMPUTED' && event.payload?.waves) {
        setWaves(event.payload.waves);
      }
      if (event.type === 'WAVE_START' && event.payload?.wave_index !== undefined) {
        setActiveWave(event.payload.wave_index);
      }
      if (event.type === 'SUBTASK_DONE' && event.payload?.task_id) {
        setDoneTaskIds(prev => new Set([...prev, event.payload.task_id]));
      }
      if (event.type === 'TASK_COMPLETE') {
        setActiveWave(null);
        setTimeout(() => setActiveTab('report'), 600);
      }
    });
    socketRef.current = ws;

    pollRef.current = setInterval(async () => {
      const t = await getTask(id).catch(() => null);
      if (t) {
        setTask(t);
        if (['DONE', 'FAILED'].includes(t.status)) clearInterval(pollRef.current!);
      }
    }, 3000);

    return () => { ws.close(); clearInterval(pollRef.current!); };
  }, [id]);

  if (error) return (
    <div style={{ textAlign: 'center', padding: '5rem 0', color: 'var(--text-muted)' }}>{error}</div>
  );

  if (!task) return (
    <div style={{ textAlign: 'center', padding: '5rem 0' }}>
      <div style={{ width: 32, height: 32, border: '2px solid rgba(96,165,250,0.2)', borderTopColor: 'var(--blue-bright)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const isDone   = task.status === 'DONE';
  const isFailed = task.status === 'FAILED';
  const isActive = !isDone && !isFailed;
  const isResearching = task.status === 'RESEARCHING';

  return (
    <div className="animate-fade-up" style={{ maxWidth: '860px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
          <h1 style={{ fontFamily: 'var(--font-syne)', fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', flex: 1, lineHeight: 1.4 }}>
            {task.prompt}
          </h1>
          <StatusBadge status={task.status as TaskStatus} pulse={isActive} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          <span>{task.id}</span>
          <span>·</span>
          <span>{new Date(task.created_at).toLocaleString()}</span>
          {task.revision_count > 0 && (
            <>
              <span>·</span>
              <span style={{ color: 'var(--amber)' }}>{task.revision_count} revision{task.revision_count > 1 ? 's' : ''}</span>
            </>
          )}
        </div>
      </div>

      {/* ── Pipeline Visualization ── */}
      <div className="glass" style={{ padding: '24px' }}>
        <PipelineViz status={task.status as TaskStatus} revisionCount={task.revision_count} />
      </div>

      {/* ── Wave Execution Panel ── */}
      {waves.length > 0 && (
        <div className="glass" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Research Execution Waves
            </p>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--text-muted)', background: 'rgba(96,165,250,0.08)', border: '1px solid var(--border)', borderRadius: '999px', padding: '2px 10px' }}>
              {waves.length} wave{waves.length > 1 ? 's' : ''} · {waves.reduce((acc, w) => acc + w.tasks.length, 0)} tasks
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {waves.map((wave, wi) => {
              const isWaveActive = isResearching && activeWave === wi;
              const isWaveDone   = isDone || (isResearching && activeWave !== null && activeWave > wi) || (!isResearching && !isActive);

              return (
                <div key={wi} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  {/* Wave label */}
                  <div style={{
                    minWidth: '64px', padding: '4px 8px', borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)', fontSize: '0.65rem', textAlign: 'center',
                    background: isWaveActive ? 'var(--blue-glow)' : isWaveDone ? 'var(--green-glow)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isWaveActive ? 'rgba(96,165,250,0.3)' : isWaveDone ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
                    color: isWaveActive ? 'var(--blue-bright)' : isWaveDone ? 'var(--green)' : 'var(--text-muted)',
                    transition: 'all 0.3s ease',
                  }}>
                    {isWaveDone ? '✓' : isWaveActive ? '⟳' : '○'} W{wi + 1}
                  </div>

                  {/* Tasks in this wave — shown side by side (parallel) */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', flex: 1 }}>
                    {wave.tasks.map((t) => {
                      const isDoneTask = doneTaskIds.has(t.id) || isWaveDone;
                      const isActiveTask = isWaveActive;

                      return (
                        <div key={t.id} style={{
                          padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                          fontFamily: 'var(--font-syne)', fontSize: '0.75rem',
                          background: isDoneTask ? 'var(--green-glow)' : isActiveTask ? 'var(--blue-glow)' : 'rgba(255,255,255,0.02)',
                          border: `1px solid ${isDoneTask ? 'rgba(52,211,153,0.25)' : isActiveTask ? 'rgba(96,165,250,0.25)' : 'var(--border)'}`,
                          color: isDoneTask ? 'var(--green)' : isActiveTask ? 'var(--blue-bright)' : 'var(--text-muted)',
                          transition: 'all 0.3s ease',
                          display: 'flex', alignItems: 'center', gap: '6px',
                        }}>
                          {isActiveTask && !isDoneTask && (
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--blue-bright)', display: 'inline-block', animation: 'pulse-ring 1.2s ease infinite' }} />
                          )}
                          {isDoneTask && <span style={{ fontSize: '0.65rem' }}>✓</span>}
                          {t.title}
                        </div>
                      );
                    })}

                    {/* Parallel badge if more than 1 task */}
                    {wave.tasks.length > 1 && (
                      <div style={{
                        padding: '5px 10px', borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)', fontSize: '0.62rem',
                        background: 'rgba(34,211,238,0.05)', border: '1px solid rgba(34,211,238,0.15)',
                        color: 'var(--cyan)', alignSelf: 'center',
                      }}>
                        ∥ parallel
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: '16px', marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
            {[
              { color: 'var(--blue-bright)', label: 'Active' },
              { color: 'var(--green)',       label: 'Complete' },
              { color: 'var(--text-muted)',  label: 'Pending' },
              { color: 'var(--cyan)',        label: 'Parallel execution' },
            ].map(({ color, label }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, display: 'inline-block' }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Failure Banner ── */}
      {isFailed && (
        <div style={{ background: 'var(--red-glow)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 'var(--radius-md)', padding: '14px 18px', color: 'var(--red)', fontSize: '0.85rem' }}>
          <span style={{ fontWeight: 700 }}>Pipeline failed: </span>{task.error || 'Unknown error'}
        </div>
      )}

      {/* ── Tabs ── */}
      <div>
        <div className="tab-bar" style={{ marginBottom: '16px' }}>
          {([
            { key: 'log',    label: 'Agent Log', count: task.agent_log.length },
            { key: 'report', label: 'Report',    disabled: !isDone },
            { key: 'raw',    label: 'Raw JSON' },
          ] as { key: Tab; label: string; count?: number; disabled?: boolean }[]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => !tab.disabled && setActiveTab(tab.key)}
              disabled={tab.disabled}
              className={`tab-item ${activeTab === tab.key ? 'active' : ''}`}
              style={{ opacity: tab.disabled ? 0.3 : 1, cursor: tab.disabled ? 'not-allowed' : 'pointer' }}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span style={{ marginLeft: '6px', background: 'rgba(96,165,250,0.1)', color: 'var(--blue-bright)', fontSize: '0.65rem', padding: '1px 6px', borderRadius: '999px' }}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {activeTab === 'log' && (
          <div className="glass" style={{ padding: '16px', maxHeight: '520px', overflowY: 'auto' }}>
            <AgentLog entries={task.agent_log} />
            {isActive && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                <div style={{ width: 12, height: 12, border: '2px solid rgba(96,165,250,0.2)', borderTopColor: 'var(--blue-bright)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                Pipeline running…
              </div>
            )}
          </div>
        )}

        {activeTab === 'report' && task.result && (
          <ReportViewer result={task.result} />
        )}

        {activeTab === 'raw' && (
          <pre className="glass" style={{ padding: '20px', fontSize: '0.72rem', color: 'var(--text-secondary)', overflowX: 'auto', maxHeight: '600px', fontFamily: 'var(--font-mono)' }}>
            {JSON.stringify(task, null, 2)}
          </pre>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}