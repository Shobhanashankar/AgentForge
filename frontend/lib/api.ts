// lib/api.ts — updated to pass pipeline_config on task submission
import { PipelineConfig } from '@/components/pipeline/PipelineConfigPanel';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function submitTask(prompt: string, pipeline_config?: PipelineConfig) {
  const res = await fetch(`${BASE}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, pipeline_config }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { task_id, status, prompt }
}

export async function getTask(task_id: string) {
  const res = await fetch(`${BASE}/api/tasks/${task_id}`);
  if (!res.ok) throw new Error('Task not found');
  return res.json();
}

export async function listTasks() {
  const res = await fetch(`${BASE}/api/tasks`);
  if (!res.ok) throw new Error('Failed to list tasks');
  return res.json();
}

export function createTaskSocket(
  task_id: string,
  onEvent: (event: any) => void,
): WebSocket {
  const wsBase = BASE.replace(/^http/, 'ws');
  const ws = new WebSocket(`${wsBase}/ws/tasks/${task_id}`);
  ws.onmessage = (msg) => {
    try { onEvent(JSON.parse(msg.data)); } catch {}
  };
  return ws;
}