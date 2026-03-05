'use client';
import { AgentLogEntry } from '@/lib/types';

const EVENT_STYLES: Record<string, { dot: string; label: string; text: string }> = {
  STATE_CHANGE:        { dot: 'bg-slate-500',   label: 'STATE',    text: 'text-slate-400' },
  AGENT_DONE:          { dot: 'bg-emerald-500', label: 'DONE',     text: 'text-emerald-400' },
  AGENT_FAILED:        { dot: 'bg-red-500',      label: 'FAILED',   text: 'text-red-400' },
  REVISION_REQUESTED:  { dot: 'bg-orange-500',   label: 'REVISION', text: 'text-orange-400' },
  TASK_COMPLETE:       { dot: 'bg-emerald-400',  label: 'COMPLETE', text: 'text-emerald-300' },
  TASK_FAILED:         { dot: 'bg-red-400',      label: 'FAILED',   text: 'text-red-300' },
};

const AGENT_COLORS: Record<string, string> = {
  PlannerAgent:    'text-blue-400',
  ResearcherAgent: 'text-violet-400',
  WriterAgent:     'text-amber-400',
  ReviewerAgent:   'text-cyan-400',
  Orchestrator:    'text-slate-400',
};

interface Props {
  entries: AgentLogEntry[];
}

export default function AgentLog({ entries }: Props) {
  if (!entries.length) {
    return (
      <div className="text-center py-12 text-slate-600 text-sm">
        Agent activity will appear here once the pipeline starts.
      </div>
    );
  }

  return (
    <div className="space-y-1 font-mono text-xs">
      {entries.map((entry, i) => {
        const style = EVENT_STYLES[entry.event] || EVENT_STYLES.STATE_CHANGE;
        const agentColor = AGENT_COLORS[entry.agent] || 'text-slate-400';
        const time = new Date(entry.timestamp).toLocaleTimeString('en-US', {
          hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
        });

        return (
          <div
            key={i}
            className="flex items-start gap-3 py-2 px-3 rounded-lg hover:bg-white/[0.02] transition-colors group"
          >
            {/* Timeline dot */}
            <div className="flex flex-col items-center flex-shrink-0 mt-1">
              <div className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              {i < entries.length - 1 && (
                <div className="w-px h-full bg-slate-800 mt-1 group-last:hidden" style={{minHeight:'12px'}} />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-slate-600">{time}</span>
                <span className={`text-[10px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded ${style.text} border border-current opacity-70`}>
                  {style.label}
                </span>
                <span className={`font-semibold ${agentColor}`}>{entry.agent}</span>
              </div>
              <p className="text-slate-300 mt-0.5 leading-relaxed">{entry.message}</p>

              {/* Show feedback items if present */}
              {entry.payload?.feedback && entry.payload.feedback.length > 0 && (
                <div className="mt-1.5 space-y-0.5">
                  {entry.payload.feedback.map((f: any, fi: number) => (
                    <div key={fi} className="text-orange-400/80 pl-2 border-l border-orange-800">
                      <span className="text-orange-500">{f.section}: </span>{f.comment}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
