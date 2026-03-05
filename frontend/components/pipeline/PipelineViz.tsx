'use client';
import { TaskStatus, PIPELINE_STAGES, AgentName } from '@/lib/types';

const AGENT_ICONS: Record<AgentName, string> = {
  PlannerAgent:    '🗺',
  ResearcherAgent: '🔬',
  WriterAgent:     '✍️',
  ReviewerAgent:   '🔍',
  Orchestrator:    '⚙️',
};

const STAGE_COLORS: Record<string, { ring: string; bg: string; text: string; glow: string }> = {
  pending:  { ring: 'border-slate-700', bg: 'bg-slate-900',  text: 'text-slate-500', glow: '' },
  active:   { ring: 'border-blue-500',  bg: 'bg-blue-950',   text: 'text-blue-300',  glow: 'shadow-[0_0_20px_rgba(59,130,246,0.4)]' },
  revising: { ring: 'border-orange-500',bg: 'bg-orange-950', text: 'text-orange-300',glow: 'shadow-[0_0_20px_rgba(249,115,22,0.4)]' },
  done:     { ring: 'border-emerald-500',bg: 'bg-emerald-950',text: 'text-emerald-300',glow: 'shadow-[0_0_14px_rgba(16,185,129,0.3)]' },
};

function getStageState(
  stageStatus: TaskStatus,
  currentStatus: TaskStatus,
  revisionCount: number,
): 'pending' | 'active' | 'revising' | 'done' {
  const order: TaskStatus[] = ['IDLE','PLANNING','RESEARCHING','WRITING','REVIEWING','REVISING','DONE','FAILED'];

  if (currentStatus === 'REVISING' && stageStatus === 'WRITING') return 'revising';
  if (stageStatus === currentStatus) return 'active';

  const ci = order.indexOf(currentStatus);
  const si = order.indexOf(stageStatus);
  if (ci > si) return 'done';
  return 'pending';
}

interface Props {
  status: TaskStatus;
  revisionCount: number;
}

export default function PipelineViz({ status, revisionCount }: Props) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between gap-2">
        {PIPELINE_STAGES.map((stage, i) => {
          const state = getStageState(stage.status, status, revisionCount);
          const colors = STAGE_COLORS[state];
          const isLast = i === PIPELINE_STAGES.length - 1;

          return (
            <div key={stage.agent} className="flex items-center flex-1">
              {/* Node */}
              <div className="flex flex-col items-center gap-2 flex-shrink-0">
                <div
                  className={`
                    relative w-16 h-16 rounded-2xl border-2 flex items-center justify-center
                    transition-all duration-500 ${colors.ring} ${colors.bg} ${colors.glow}
                  `}
                >
                  {/* Pulse ring for active */}
                  {state === 'active' && (
                    <div className="absolute inset-0 rounded-2xl border-2 border-blue-400 animate-ping opacity-30" />
                  )}
                  {state === 'revising' && (
                    <div className="absolute inset-0 rounded-2xl border-2 border-orange-400 animate-ping opacity-30" />
                  )}

                  <span className="text-2xl">
                    {state === 'done' ? '✓' : AGENT_ICONS[stage.agent]}
                  </span>
                </div>

                <div className="text-center">
                  <p className={`text-xs font-semibold tracking-wider uppercase ${colors.text} transition-colors duration-300`}>
                    {stage.label}
                  </p>
                  {state === 'active' && (
                    <p className="text-xs text-blue-400 animate-pulse mt-0.5">running...</p>
                  )}
                  {state === 'revising' && (
                    <p className="text-xs text-orange-400 animate-pulse mt-0.5">revising...</p>
                  )}
                  {state === 'done' && (
                    <p className="text-xs text-emerald-500 mt-0.5">done</p>
                  )}
                </div>
              </div>

              {/* Connector arrow */}
              {!isLast && (
                <div className="flex-1 flex items-center justify-center mx-1 mb-8">
                  <div className={`h-px flex-1 transition-colors duration-500 ${
                    state === 'done' ? 'bg-emerald-700' : 'bg-slate-700'
                  }`} />
                  <svg width="10" height="10" viewBox="0 0 10 10" className={`flex-shrink-0 transition-colors duration-500 ${
                    state === 'done' ? 'text-emerald-700' : 'text-slate-700'
                  }`}>
                    <path d="M0 5 L7 1 L7 9 Z" fill="currentColor" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Revision indicator */}
      {revisionCount > 0 && status !== 'DONE' && status !== 'FAILED' && (
        <div className="mt-4 flex items-center gap-2 justify-center">
          <div className="flex items-center gap-1.5 bg-orange-950 border border-orange-800 rounded-full px-3 py-1">
            <span className="text-orange-400 text-xs">↩</span>
            <span className="text-orange-300 text-xs font-medium">
              Revision cycle {revisionCount} / 3
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
