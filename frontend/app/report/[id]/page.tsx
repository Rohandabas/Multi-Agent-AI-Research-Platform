'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getReport, downloadExport, getChartUrl } from '@/lib/api';
import type { Report, EvalMetrics } from '@/types/research';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import Image from 'next/image';

function MetricBar({ label, value, color }: { label: string; value: number | null; color: string }) {
  const pct = value !== null ? Math.round(value * 100) : null;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className={`font-medium ${color}`}>{pct !== null ? `${pct}%` : '—'}</span>
      </div>
      <div className="h-1.5 bg-[#1a1a3a] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${color.replace('text-', 'bg-')}`}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const reportId = params.id as string;
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'report' | 'sources' | 'metrics'>('report');

  useEffect(() => {
    getReport(reportId)
      .then(setReport)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [reportId]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-animated flex items-center justify-center">
        <div className="text-center">
          <div className="spin w-12 h-12 border-2 border-indigo-500/30 border-t-indigo-400 rounded-full mx-auto mb-4" />
          <p className="text-slate-400">Loading report...</p>
        </div>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="min-h-screen bg-gradient-animated flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400 mb-4">Report not found.</p>
          <Link href="/" className="text-indigo-400 hover:text-indigo-300">← Back to home</Link>
        </div>
      </main>
    );
  }

  const metrics = report.eval_metrics;
  const duration = report.duration_seconds
    ? `${Math.floor(report.duration_seconds / 60)}m ${Math.round(report.duration_seconds % 60)}s`
    : '—';

  return (
    <main className="min-h-screen bg-gradient-animated">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#2a2a4a]/50 glass sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold"
            >
              ∞
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-slate-200 truncate max-w-md">
                {report.query}
              </h1>
              <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                <span>{new Date(report.created_at).toLocaleDateString()}</span>
                <span>·</span>
                <span>⏱ {duration}</span>
                <span>·</span>
                <span>💰 ${report.total_cost_usd.toFixed(4)}</span>
                <span>·</span>
                <span className="text-emerald-400 capitalize">{report.status}</span>
              </div>
            </div>
          </div>

          {/* Export buttons */}
          <div className="flex items-center gap-2">
            {report.pdf_path && (
              <button
                id="download-pdf-btn"
                onClick={() => downloadExport(reportId, 'pdf')}
                className="px-4 py-2 rounded-xl bg-red-600/20 border border-red-500/30 text-red-400 text-sm font-medium hover:bg-red-600/30 transition-colors"
              >
                📑 PDF
              </button>
            )}
            {report.docx_path && (
              <button
                id="download-docx-btn"
                onClick={() => downloadExport(reportId, 'docx')}
                className="px-4 py-2 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400 text-sm font-medium hover:bg-blue-600/30 transition-colors"
              >
                📝 DOCX
              </button>
            )}
            {report.markdown_path && (
              <button
                id="download-md-btn"
                onClick={() => downloadExport(reportId, 'markdown')}
                className="px-4 py-2 rounded-xl bg-slate-600/20 border border-slate-500/30 text-slate-400 text-sm font-medium hover:bg-slate-600/30 transition-colors"
              >
                ✍️ MD
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="xl:col-span-1 space-y-4">
          {/* Stats */}
          <div className="glass rounded-xl p-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Research Stats</h3>
            <div className="space-y-2">
              {[
                { label: 'Depth', value: report.depth },
                { label: 'Sources Used', value: `${report.sources_used.length}` },
                { label: 'Total Tokens', value: report.total_tokens.toLocaleString() },
                { label: 'Total Cost', value: `$${report.total_cost_usd.toFixed(4)}` },
                { label: 'Duration', value: duration },
              ].map(s => (
                <div key={s.label} className="flex justify-between text-sm">
                  <span className="text-slate-500">{s.label}</span>
                  <span className="text-slate-300 font-medium capitalize">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Eval Metrics */}
          {metrics && (
            <div className="glass rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Quality Metrics</h3>
              <div className="space-y-3">
                <MetricBar label="Citation Coverage" value={metrics.citation_coverage} color="text-blue-400" />
                <MetricBar label="Faithfulness" value={metrics.faithfulness} color="text-emerald-400" />
                <MetricBar label="Completeness" value={metrics.completeness} color="text-purple-400" />
                <MetricBar
                  label="Hallucination Risk"
                  value={metrics.hallucination_risk !== null ? 1 - (metrics.hallucination_risk ?? 0) : null}
                  color="text-yellow-400"
                />
                <MetricBar label="Retrieval Quality" value={metrics.retrieval_quality} color="text-indigo-400" />
              </div>
            </div>
          )}

          {/* Charts thumbnails */}
          {report.chart_paths.length > 0 && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Charts</h3>
              <div className="space-y-2">
                {report.chart_paths.map((_, i) => (
                  <div key={i} className="rounded-lg overflow-hidden border border-[#2a2a4a]">
                    <img
                      src={getChartUrl(reportId, i)}
                      alt={`Chart ${i + 1}`}
                      className="w-full object-cover"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Main content */}
        <div className="xl:col-span-3">
          {/* Tabs */}
          <div className="flex gap-1 mb-4">
            {[
              { id: 'report', label: '📄 Report' },
              { id: 'sources', label: `📚 Sources (${report.sources_used.length})` },
              { id: 'metrics', label: '📈 Metrics' },
            ].map(tab => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-indigo-600/20 border border-indigo-500/50 text-indigo-300'
                    : 'text-slate-500 hover:text-slate-300 border border-transparent'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Report tab */}
          {activeTab === 'report' && (
            <div className="glass rounded-2xl p-6 md:p-8">
              {report.report_markdown ? (
                <article className="report-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {report.report_markdown}
                  </ReactMarkdown>
                </article>
              ) : (
                <p className="text-slate-500 text-center py-12">
                  {report.status === 'error' ? `Error: ${report.error_message}` : 'Report not yet generated.'}
                </p>
              )}
            </div>
          )}

          {/* Sources tab */}
          {activeTab === 'sources' && (
            <div className="space-y-3">
              {report.sources_used.length === 0 ? (
                <div className="glass rounded-xl p-6 text-center text-slate-500">No sources recorded.</div>
              ) : (
                report.sources_used.map((source, i) => (
                  <div key={i} className="glass rounded-xl p-4 hover:border-indigo-500/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-indigo-400 font-mono text-xs">{source.inline_ref}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            source.source_type === 'pdf' ? 'bg-orange-500/20 text-orange-400' :
                            source.source_type === 'academic' ? 'bg-purple-500/20 text-purple-400' :
                            source.source_type === 'sec' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-slate-500/20 text-slate-400'
                          }`}>
                            {source.source_type.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300 font-medium truncate">{source.title}</p>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-slate-500 hover:text-indigo-400 transition-colors truncate block mt-0.5"
                        >
                          {source.url}
                        </a>
                      </div>
                      <div className="text-xs text-slate-600 flex-shrink-0">
                        {source.credibility_score ? `${Math.round(source.credibility_score * 100)}%` : ''}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Metrics tab */}
          {activeTab === 'metrics' && (
            <div className="glass rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-slate-200 mb-6">Report Quality Analysis</h3>
              {metrics ? (
                <div className="space-y-6">
                  {[
                    {
                      metric: 'Citation Coverage',
                      value: metrics.citation_coverage,
                      desc: 'Percentage of factual claims supported by inline citations',
                      color: 'text-blue-400',
                    },
                    {
                      metric: 'Faithfulness',
                      value: metrics.faithfulness,
                      desc: 'How accurately the report reflects the source documents',
                      color: 'text-emerald-400',
                    },
                    {
                      metric: 'Completeness',
                      value: metrics.completeness,
                      desc: 'Percentage of planned report sections successfully generated',
                      color: 'text-purple-400',
                    },
                    {
                      metric: 'Retrieval Quality',
                      value: metrics.retrieval_quality,
                      desc: 'Ratio of verified facts to total extracted facts',
                      color: 'text-indigo-400',
                    },
                    {
                      metric: 'Hallucination Safety',
                      value: metrics.hallucination_risk !== null ? 1 - (metrics.hallucination_risk ?? 0) : null,
                      desc: 'Inverse of hallucination risk — higher is safer',
                      color: 'text-yellow-400',
                    },
                  ].map(m => (
                    <div key={m.metric}>
                      <div className="flex justify-between items-center mb-2">
                        <div>
                          <span className={`text-sm font-medium ${m.color}`}>{m.metric}</span>
                          <p className="text-xs text-slate-600 mt-0.5">{m.desc}</p>
                        </div>
                        <span className={`text-2xl font-bold ${m.color}`}>
                          {m.value !== null ? `${Math.round(m.value * 100)}%` : '—'}
                        </span>
                      </div>
                      <div className="h-2 bg-[#1a1a3a] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-1000 ${m.color.replace('text-', 'bg-')}`}
                          style={{ width: `${m.value !== null ? Math.round(m.value * 100) : 0}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-center py-8">No evaluation metrics available.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
