import { useState } from 'react';
import ReportUploader from './components/ReportUploader';
import SummaryView from './components/SummaryView';
import QAChat from './components/QAChat';
import EvalPanel from './components/EvalPanel';
import CompareView, { type CompareEntry } from './components/CompareView';
import { generateSummaryStream } from './services/api';
import type { ReportMeta, StructuredSummary } from './types';

type Tab = 'summary' | 'qa' | 'eval' | 'compare';

// 评分（测试）标签页：交付版隐藏；需要调试时改回 true
const SHOW_EVAL = false;

interface ReportEntry {
  meta: ReportMeta;
  summary: StructuredSummary;
}

function App() {
  const [library, setLibrary] = useState<ReportEntry[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [showUploader, setShowUploader] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>('summary');
  const [error, setError] = useState('');

  const current = library.find((e) => e.meta.id === currentId) ?? null;

  async function handleUploaded(r: ReportMeta) {
    setError('');
    setLoading(true);
    setStreamText('');
    try {
      const s = await generateSummaryStream(r.id, (t) =>
        setStreamText((prev) => prev + t),
      );
      setLibrary((prev) => [...prev, { meta: r, summary: s }]);
      setCurrentId(r.id);
      setStreamText('');
      setShowUploader(false);
      setTab('summary');
    } catch (e) {
      setError(e instanceof Error ? e.message : '摘要生成失败，请检查 API Key 配置');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">FinInsight</h1>
            <p className="text-sm text-gray-400">
              行业研报智能分析与问答系统 · 个人/活动作品
            </p>
          </div>
          {current && (
            <div className="text-right text-sm text-gray-500">
              <p className="font-medium text-gray-700">
                {current.meta.title ?? current.meta.filename}
              </p>
              <p>
                {current.meta.page_count} 页 ·{' '}
                {current.meta.char_count.toLocaleString()} 字
              </p>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        {library.length === 0 && !showUploader && !loading && (
          <ReportUploader onUploaded={handleUploaded} />
        )}

        {showUploader && !loading && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">添加另一份研报</p>
              <button
                onClick={() => setShowUploader(false)}
                className="text-sm text-gray-400 hover:text-gray-600"
              >
                取消
              </button>
            </div>
            <ReportUploader onUploaded={handleUploaded} />
          </div>
        )}

        {loading && (
          <div className="mb-6">
            <div className="text-center mb-3">
              <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full" />
              <p className="text-gray-500 mt-2">
                正在调用 Hy3 生成结构化摘要...
              </p>
            </div>
            {streamText && (
              <div>
                <p className="text-xs text-gray-400 mb-1">
                  模型原始输出（实时）
                </p>
                <pre className="bg-gray-900 text-gray-100 text-xs rounded-lg p-4 overflow-auto max-h-80 whitespace-pre-wrap">
                  {streamText}
                </pre>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
            {error}
          </div>
        )}

        {current && (
          <>
            <div className="flex flex-wrap gap-2 mb-4">
              {library.map((e) => (
                <button
                  key={e.meta.id}
                  onClick={() => setCurrentId(e.meta.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    e.meta.id === currentId
                      ? 'bg-blue-500 text-white'
                      : 'bg-white border text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {e.meta.title ?? e.meta.filename}
                </button>
              ))}
              <button
                onClick={() => setShowUploader(true)}
                className="px-3 py-1.5 rounded-full text-xs font-medium bg-white border border-dashed border-gray-300 text-gray-500 hover:border-blue-400 hover:text-blue-500"
              >
                ＋ 添加报告
              </button>
            </div>

            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setTab('summary')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === 'summary'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white border text-gray-600 hover:bg-gray-50'
                }`}
              >
                结构化摘要
              </button>
              <button
                onClick={() => setTab('qa')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === 'qa'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white border text-gray-600 hover:bg-gray-50'
                }`}
              >
                研报问答
              </button>
              {SHOW_EVAL && (
                <button
                  onClick={() => setTab('eval')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    tab === 'eval'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white border text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  评分（测试）
                </button>
              )}
              <button
                onClick={() => setTab('compare')}
                disabled={library.length < 2}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                  tab === 'compare'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white border text-gray-600 hover:bg-gray-50'
                }`}
              >
                多报告对比{library.length < 2 ? '（需 ≥2 份）' : ''}
              </button>
            </div>

            {tab === 'summary' && <SummaryView summary={current.summary} />}
            {tab === 'qa' && <QAChat reportId={current.meta.id} />}
            {tab === 'eval' && SHOW_EVAL && (
              <EvalPanel reportId={current.meta.id} summary={current.summary} />
            )}
            {tab === 'compare' && (
              <CompareView reports={library as CompareEntry[]} />
            )}
          </>
        )}
      </main>

      <footer className="text-center py-6 text-xs text-gray-400">
        FinInsight · 基于 Hy3 构建 · 仅供参考，不构成投资建议
      </footer>
    </div>
  );
}

export default App;
