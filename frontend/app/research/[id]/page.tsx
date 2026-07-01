'use client';

import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useResearchSocket } from '@/hooks/useResearchSocket';
import type { AgentStatus } from '@/types/research';

const AGENT_ICONS: Record<string, string> = {
  PlannerAgent: '🧠',
  SearchAgent: '🔍',
  PDFAgent: '📄',
  MemoryAgent: '💾',
  ExtractorAgent: '⚙️',
  FactCheckerAgent: '✅',
  WriterAgent: '✍️',
  ChartGeneratorAgent: '📊',
  ExporterAgent: '📤',
  EvaluatorAgent: '📈',
};

function AgentCard({ agent }: { agent: AgentStatus }) {
  const icon = AGENT_ICONS[agent.name] || '🤖';
  const isRunning = agent.status === 'running';
  const isComplete = agent.status === 'complete';
  const isError = agent.status === 'error';
  const isPending = agent.status === 'pending';

  return (
    <div
      className={`glass rounded-xl p-3 transition-all duration-500 border ${
        isRunning
          ? 'border-indigo-500/60 shadow-lg shadow-indigo-500/20 scale-[1.02]'
          : isComplete
          ? 'border-emerald-500/40'
          : isError
          ? 'border-red-500/40'
          : 'border-[#2a2a4a]'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`text-xl w-8 text-center ${isPending ? 'opacity-40' : ''}`}>{icon}</div>
        <div className="flex-1 min-w-0">
          <div className={`text-sm font-medium truncate ${
            isRunning ? 'text-indigo-300' :
            isComplete ? 'text-emerald-400' :
            isError ? 'text-red-400' :
            'text-slate-500'
          }`}>
            {agent.displayName}
          </div>
          {agent.message && !isPending && (
            <div className="text-xs text-slate-600 truncate mt-0.5">{agent.message}</div>
          )}
        </div>
        <div className="flex-shrink-0">
          {isRunning && (
            <div className="spin w-4 h-4 border-2 border-indigo-500/30 border-t-indigo-400 rounded-full" />
          )}
          {isComplete && <span className="text-emerald-400 text-sm">✓</span>}
          {isError && <span className="text-red-400 text-sm">✗</span>}
          {isPending && <span className="text-slate-700 text-xs">○</span>}
        </div>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = params.id as string;
  const reportId = searchParams.get('reportId');

  const { isConnected, progress, costSoFar, events, agentStatuses, isComplete, isError } =
    useResearchSocket(jobId);

  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isComplete && reportId) {
      setTimeout(() => {
        router.push(`/report/${reportId}`);
      }, 1500);
    }
  }, [isComplete, reportId, router]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  const recentEvents = events.slice(-5).reverse();

  return (
    <main className="min-h-screen bg-gradient-animated">
      {/* Header */}
      <header className="px-8 py-5 flex items-center justify-between border-b border-[#2a2a4a]/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold">
            ∞
          </div>
          <span className="font-semibold text-slate-300">ResearchAI</span>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <span className={`flex items-center gap-1.5 ${isConnected ? 'text-emerald-400' : 'text-slate-500'}`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 pulse-dot' : 'bg-slate-600'}`} />
            {isConnected ? 'Connected' : 'Connecting...'}
          </span>
          <span className="text-slate-500">⏱ {formatElapsed(elapsed)}</span>
          <span className="text-slate-500">💰 ${costSoFar.toFixed(4)}</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Agents */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            Agent Pipeline
          </h2>
          {agentStatuses.map(agent => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>

        {/* Right: Progress + Events */}
        <div className="lg:col-span-2 space-y-5">
          {/* Progress card */}
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-200">
                {isComplete ? '🎉 Research Complete!' : isError ? '❌ Research Failed' : '⚡ Researching...'}
              </h2>
              <span className={`text-2xl font-bold ${
                isComplete ? 'text-emerald-400' : 'gradient-text'
              }`}>
                {progress}%
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-[#1a1a3a] rounded-full overflow-hidden mb-4">
              <div
                className="progress-bar"
                style={{ width: `${progress}%` }}
              />
            </div>

            {isComplete && reportId && (
              <div className="text-center py-4 fade-in-up">
                <p className="text-emerald-400 font-medium mb-3">Report ready! Redirecting...</p>
                <button
                  onClick={() => router.push(`/report/${reportId}`)}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl text-white font-medium hover:from-emerald-500 hover:to-teal-500 transition-all"
                >
                  View Report →
                </button>
              </div>
            )}
          </div>

          {/* Live events log */}
          <div className="glass rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
              Live Activity Log
            </h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {events.length === 0 ? (
                <p className="text-slate-600 text-sm text-center py-6">
                  Waiting for connection...
                </p>
              ) : (
                [...events].reverse().map((event, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 py-2 px-3 rounded-lg text-sm transition-all ${
                      event.event === 'agent_start'
                        ? 'bg-indigo-500/10 border border-indigo-500/20'
                        : event.event === 'agent_complete'
                        ? 'bg-emerald-500/10 border border-emerald-500/20'
                        : event.event === 'agent_error'
                        ? 'bg-red-500/10 border border-red-500/20'
                        : event.event === 'report_ready'
                        ? 'bg-purple-500/10 border border-purple-500/20'
                        : 'bg-[#0d0d22]'
                    }`}
                  >
                    <span className="text-slate-600 text-xs mt-0.5 flex-shrink-0">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`flex-1 ${
                      event.event === 'agent_start' ? 'text-indigo-300' :
                      event.event === 'agent_complete' ? 'text-emerald-400' :
                      event.event === 'agent_error' ? 'text-red-400' :
                      event.event === 'report_ready' ? 'text-purple-300' :
                      'text-slate-400'
                    }`}>
                      {event.agent && <strong>[{event.agent}]</strong>} {event.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
