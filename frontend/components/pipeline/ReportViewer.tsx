'use client';
import { TaskResult } from '@/lib/types';

interface Props {
  result: TaskResult;
}

// Minimal Markdown → HTML renderer (no external deps needed)
function renderMarkdown(md: string): string {
  return md
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mb-2 mt-6 first:mt-0">$1</h1>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-slate-200 mb-2 mt-5 pb-1 border-b border-slate-800">$2</h2>')
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-slate-300 mb-1 mt-4">$3</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="text-slate-300 italic">$1</em>')
    .replace(/^---$/gm, '<hr class="border-slate-800 my-4" />')
    .replace(/^- (.+)$/gm, '<li class="text-slate-300 ml-4 list-disc list-inside mb-0.5">$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li class="text-slate-300 ml-4 list-decimal list-inside mb-0.5">$1</li>')
    .replace(/^(?!<[h|l|h|i])(.+)$/gm, '<p class="text-slate-400 leading-relaxed mb-2">$1</p>')
    .replace(/<\/p>\n<p/g, '</p><p')
    .replace(/\n{2,}/g, '\n');
}

export default function ReportViewer({ result }: Props) {
  const html = renderMarkdown(result.report || '');

  return (
    <div className="space-y-4">
      {/* Meta bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 bg-emerald-950 border border-emerald-800 rounded-full px-3 py-1">
          <span className="text-emerald-400 text-sm">✓</span>
          <span className="text-emerald-300 text-xs font-medium">
            Score: {result.score}/100
          </span>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700 rounded-full px-3 py-1">
          <span className="text-slate-400 text-xs">{result.word_count} words</span>
        </div>
        {result.revision_count > 0 && (
          <div className="flex items-center gap-1.5 bg-orange-950 border border-orange-800 rounded-full px-3 py-1">
            <span className="text-orange-300 text-xs">{result.revision_count} revision{result.revision_count > 1 ? 's' : ''}</span>
          </div>
        )}
        {result.approved === false && (
          <div className="flex items-center gap-1.5 bg-yellow-950 border border-yellow-800 rounded-full px-3 py-1">
            <span className="text-yellow-300 text-xs">⚠ Max revisions reached — best-effort report</span>
          </div>
        )}
      </div>

      {/* Report body */}
      <div
        className="prose-sm max-w-none bg-slate-950 border border-slate-800 rounded-xl p-6 overflow-auto"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
