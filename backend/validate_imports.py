"""Validate all backend imports."""
import sys
import os
sys.path.insert(0, '.')
os.environ.setdefault('GOOGLE_API_KEY', 'test')
os.environ.setdefault('TAVILY_API_KEY', 'test')

errors = []
checks = []

def check(label, fn):
    try:
        fn()
        checks.append(f'[OK] {label}')
    except Exception as e:
        errors.append(f'[ERR] {label}: {str(e)[:120]}')

check('settings', lambda: __import__('app.config.settings', fromlist=['settings']))
check('constants', lambda: __import__('app.config.constants', fromlist=['DEPTH_CONFIG']))
check('errors', lambda: [
    __import__('app.errors.base', fromlist=['ResearchException']),
    __import__('app.errors.agent', fromlist=['FactCheckException']),
    __import__('app.errors.search', fromlist=['SearchException']),
    __import__('app.errors.pdf', fromlist=['PDFException']),
    __import__('app.errors.export', fromlist=['ExportException']),
])
check('schemas', lambda: [
    __import__('app.schemas.request', fromlist=['ResearchConfig']),
    __import__('app.schemas.response', fromlist=['AgentResult', 'ProgressEvent']),
    __import__('app.schemas.internal', fromlist=['ExtractedFact']),
])
check('tools', lambda: [
    __import__('app.tools.base', fromlist=['BaseLLMTool']),
    __import__('app.tools.llm.gemini', fromlist=['GeminiTool']),
    __import__('app.tools.llm.groq', fromlist=['GroqTool']),
])
check('services', lambda: [
    __import__('app.services.citation_manager', fromlist=['CitationManager']),
    __import__('app.services.cost_tracker', fromlist=['CostTracker']),
    __import__('app.services.job_manager', fromlist=['job_manager']),
])
check('rag', lambda: [
    __import__('app.rag.chunker', fromlist=['TextChunker']),
    __import__('app.rag.reranker', fromlist=['Reranker']),
])
check('graph', lambda: __import__('app.graph.state', fromlist=['ResearchState']))
check('agents', lambda: __import__('app.agents.base', fromlist=['BaseAgent']))

print('RESULTS:')
for c in checks:
    print('  ' + c)
for e in errors:
    print('  ' + e)

if not errors:
    print('\nALL IMPORTS PASS!')
else:
    print(f'\n{len(errors)} ERRORS, {len(checks)} OK')
