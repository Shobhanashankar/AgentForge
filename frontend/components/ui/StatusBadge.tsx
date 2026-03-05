import { TaskStatus, STATUS_COLORS } from '@/lib/types';

const STATUS_LABELS: Record<TaskStatus, string> = {
  IDLE:        'Queued',
  PLANNING:    'Planning',
  RESEARCHING: 'Researching',
  WRITING:     'Writing',
  REVIEWING:   'Reviewing',
  REVISING:    'Revising',
  DONE:        'Complete',
  FAILED:      'Failed',
};

const STATUS_BG: Record<TaskStatus, string> = {
  IDLE:        'bg-slate-900 border-slate-700',
  PLANNING:    'bg-blue-950 border-blue-800',
  RESEARCHING: 'bg-violet-950 border-violet-800',
  WRITING:     'bg-amber-950 border-amber-800',
  REVIEWING:   'bg-cyan-950 border-cyan-800',
  REVISING:    'bg-orange-950 border-orange-800',
  DONE:        'bg-emerald-950 border-emerald-800',
  FAILED:      'bg-red-950 border-red-800',
};

interface Props {
  status: TaskStatus;
  pulse?: boolean;
}

export default function StatusBadge({ status, pulse }: Props) {
  const shouldPulse = pulse && !['DONE', 'FAILED', 'IDLE'].includes(status);
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${STATUS_BG[status]} ${STATUS_COLORS[status]}`}>
      {shouldPulse && (
        <span className={`w-1.5 h-1.5 rounded-full ${STATUS_COLORS[status].replace('text-', 'bg-')} animate-pulse`} />
      )}
      {STATUS_LABELS[status]}
    </span>
  );
}
