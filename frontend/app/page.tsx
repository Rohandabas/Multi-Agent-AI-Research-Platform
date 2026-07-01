'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { startResearch } from '@/lib/api';
import type { ResearchConfig, Depth } from '@/types/research';
import { DEFAULT_CONFIG } from '@/types/research';

const DEPTH_INFO = {
  quick: { label: 'Quick', time: '~1 min', desc: '5 searches, 1 PDF', color: 'text-emerald-400' },
  standard: { label: 'Standard', time: '~3 min', desc: '10 searches, 3 PDFs', color: 'text-blue-400' },
  deep: { label: 'Deep', time: '~8 min', desc: '20 searches, 5 PDFs', color: 'text-purple-400' },
};

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState<Depth>('standard');
  const [sources, setSources] = useState<string[]>(['web', 'pdfs', 'memory']);
  const [formats, setFormats] = useState<string[]>(['pdf', 'docx', 'markdown']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleSource = (src: string) => {
    setSources(prev => prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]);
  };

  const toggleFormat = (fmt: string) => {
    setFormats(prev => prev.includes(fmt) ? prev.filter(f => f !== fmt) : [...prev, fmt]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || query.length < 10) {
      setError('Please enter a more detailed research query (at least 10 characters).');
      return;
    }
    setError('');
    setIsLoading(true);

    try {
      const config: Partial<ResearchConfig> = {
        ...DEFAULT_CONFIG,
        depth,
        sources,
        output_formats: formats,
      };

      const response = await startResearch({ query: query.trim(), config });
      router.push(`/research/${response.job_id}?reportId=${response.report_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start research. Is the backend running?');
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-animated flex flex-col">
      {/* Header */}
      <header className="px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-lg glow-primary">
            ∞
          </div>
          <span className="font-semibold text-slate-200 text-lg tracking-tight">ResearchAI</span>
        </div>
        <a
          href="/api/docs"
          className="text-sm text-slate-400 hover:text-indigo-400 transition-colors"
          target="_blank"
        >
          API Docs →
        </a>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="text-center mb-12 fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-xs text-indigo-300 mb-6 border-indigo-500/30">
            <span className="pulse-dot"></span>
            Powered by Gemini 2.0 Flash + LangGraph
          </div>

          <h1 className="text-5xl md:text-6xl font-bold mb-4 leading-tight">
            <span className="gradient-text glow-text">Autonomous</span>
            <br />
            Research Analyst
          </h1>

          <p className="text-xl text-slate-400 max-w-xl mx-auto leading-relaxed">
            Enter any research topic. Our multi-agent AI plans, searches, reads PDFs,
            verifies facts, and produces a professional report with charts and citations.
          </p>
        </div>

        {/* Main form */}
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-2xl fade-in-up"
          style={{ animationDelay: '0.1s' }}
        >
          <div className="glass rounded-2xl p-6 shadow-2xl glow-primary">
            {/* Query input */}
            <div className="mb-5">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Research Topic
              </label>
              <textarea
                id="research-query"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Research the AI chip market in 2026. Compare NVIDIA, AMD, Groq, Cerebras. Include market trends, revenues, AI products, funding, risks, and opportunities."
                className="w-full bg-[#0d0d22] border border-[#2a2a4a] rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 resize-none text-sm leading-relaxed transition-colors"
                rows={4}
              />
              <div className="flex justify-between mt-1">
                <span className="text-xs text-slate-600">{query.length} characters</span>
                {query.length < 10 && query.length > 0 && (
                  <span className="text-xs text-red-400">Minimum 10 characters</span>
                )}
              </div>
            </div>

            {/* Research Depth */}
            <div className="mb-5">
              <label className="block text-sm font-medium text-slate-300 mb-2">Research Depth</label>
              <div className="grid grid-cols-3 gap-2">
                {(Object.entries(DEPTH_INFO) as [Depth, typeof DEPTH_INFO.quick][]).map(([key, info]) => (
                  <button
                    key={key}
                    type="button"
                    id={`depth-${key}`}
                    onClick={() => setDepth(key)}
                    className={`rounded-xl px-3 py-2.5 text-left transition-all border ${
                      depth === key
                        ? 'bg-indigo-600/20 border-indigo-500 shadow-lg shadow-indigo-500/20'
                        : 'bg-[#0d0d22] border-[#2a2a4a] hover:border-[#3a3a5a]'
                    }`}
                  >
                    <div className={`text-sm font-semibold ${info.color}`}>{info.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{info.time} · {info.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Sources + Outputs row */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Sources</label>
                <div className="space-y-1.5">
                  {[
                    { id: 'web', label: 'Web Search', icon: '🌐' },
                    { id: 'pdfs', label: 'PDF Documents', icon: '📄' },
                    { id: 'memory', label: 'Prior Research', icon: '🧠' },
                  ].map(s => (
                    <label key={s.id} className="flex items-center gap-2 cursor-pointer group">
                      <input
                        id={`source-${s.id}`}
                        type="checkbox"
                        checked={sources.includes(s.id)}
                        onChange={() => toggleSource(s.id)}
                        className="w-4 h-4 rounded accent-indigo-500"
                      />
                      <span className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">
                        {s.icon} {s.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Output Formats</label>
                <div className="space-y-1.5">
                  {[
                    { id: 'pdf', label: 'PDF Report', icon: '📑' },
                    { id: 'docx', label: 'Word Document', icon: '📝' },
                    { id: 'markdown', label: 'Markdown', icon: '✍️' },
                  ].map(f => (
                    <label key={f.id} className="flex items-center gap-2 cursor-pointer group">
                      <input
                        id={`format-${f.id}`}
                        type="checkbox"
                        checked={formats.includes(f.id)}
                        onChange={() => toggleFormat(f.id)}
                        className="w-4 h-4 rounded accent-indigo-500"
                      />
                      <span className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">
                        {f.icon} {f.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              id="generate-report-btn"
              type="submit"
              disabled={isLoading || query.length < 10}
              className={`w-full py-3.5 rounded-xl font-semibold text-white transition-all ${
                isLoading || query.length < 10
                  ? 'bg-indigo-600/40 cursor-not-allowed text-indigo-300'
                  : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-[1.01] active:scale-[0.99]'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
                  Starting Research...
                </span>
              ) : (
                '⚡ Generate Research Report'
              )}
            </button>
          </div>
        </form>

        {/* Feature pills */}
        <div
          className="flex flex-wrap justify-center gap-2 mt-8 fade-in-up"
          style={{ animationDelay: '0.2s' }}
        >
          {[
            '🤖 Multi-Agent AI',
            '🔍 Web + PDF Search',
            '✅ Fact Verification',
            '📊 Auto Charts',
            '📖 Citations [1][2]',
            '📥 PDF Export',
            '📈 Quality Metrics',
          ].map(f => (
            <span key={f} className="px-3 py-1 rounded-full glass text-xs text-slate-400 border-slate-700/50">
              {f}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
