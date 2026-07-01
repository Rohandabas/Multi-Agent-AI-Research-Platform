// API client — all backend calls go through here

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Research ──────────────────────────────────────────────────────────────
import type { ResearchRequest, JobStartResponse, Report } from '@/types/research';

export async function startResearch(request: ResearchRequest): Promise<JobStartResponse> {
  return fetchJson<JobStartResponse>('/api/research', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getReport(reportId: string): Promise<Report> {
  return fetchJson<Report>(`/api/report/${reportId}`);
}

export async function listReports(limit = 20, offset = 0): Promise<Report[]> {
  return fetchJson<Report[]>(`/api/reports?limit=${limit}&offset=${offset}`);
}

export async function getJobStatus(jobId: string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`/api/job/${jobId}/status`);
}

// ─── Export ────────────────────────────────────────────────────────────────
export function getExportUrl(reportId: string, format: 'pdf' | 'docx' | 'markdown'): string {
  return `${BASE_URL}/api/export/${reportId}/${format}`;
}

export function getChartUrl(reportId: string, chartIndex: number): string {
  return `${BASE_URL}/api/export/${reportId}/chart/${chartIndex}`;
}

export async function downloadExport(reportId: string, format: 'pdf' | 'docx' | 'markdown') {
  const url = getExportUrl(reportId, format);
  const link = document.createElement('a');
  link.href = url;
  link.download = `research_report.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ─── Health ────────────────────────────────────────────────────────────────
export async function checkHealth(): Promise<{ status: string }> {
  return fetchJson<{ status: string }>('/health');
}
