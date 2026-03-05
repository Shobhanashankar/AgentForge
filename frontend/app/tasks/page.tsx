'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listTasks } from '@/lib/api';
import { TaskStatus, STATUS_COLORS } from '@/lib/types';
import StatusBadge from '@/components/ui/StatusBadge';

export default function TasksPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTasks()
      .then(setTasks)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white" style={{fontFamily:'var(--font-syne)'}}>
          Task History
        </h1>
        <Link
          href="/"
          className="text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
        >
          ← New task
        </Link>
      </div>

      {loading && (
        <div className="text-center py-16">
          <div className="w-7 h-7 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto" />
        </div>
      )}

      {!loading && tasks.length === 0 && (
        <div className="text-center py-20 space-y-3">
          <p className="text-4xl">📋</p>
          <p className="text-slate-400">No tasks yet.</p>
          <Link href="/" className="text-blue-400 hover:underline text-sm">Submit your first task →</Link>
        </div>
      )}

      {!loading && tasks.length > 0 && (
        <div className="space-y-2">
          {tasks.map((task) => (
            <Link
              key={task.id}
              href={`/tasks/${task.id}`}
              className="block bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800 hover:border-slate-700 rounded-xl px-5 py-4 transition-all duration-200 group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-slate-200 text-sm font-medium group-hover:text-white transition-colors line-clamp-2">
                    {task.prompt}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-600 font-mono">
                    <span>{task.id.slice(0, 8)}…</span>
                    <span>·</span>
                    <span>{new Date(task.created_at).toLocaleString()}</span>
                    {task.revision_count > 0 && (
                      <>
                        <span>·</span>
                        <span className="text-orange-600">{task.revision_count} rev</span>
                      </>
                    )}
                  </div>
                </div>
                <StatusBadge status={task.status as TaskStatus} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
