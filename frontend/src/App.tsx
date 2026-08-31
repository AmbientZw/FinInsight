import { useState } from 'react';
import ReportUploader from './components/ReportUploader';
import SummaryView from './components/SummaryView';
import QAChat from './components/QAChat';
import EvalPanel from './components/EvalPanel';
import { generateSummaryStream } from './services/api';
import type { ReportMeta, StructuredSummary } from './types';

type Tab = 'summary' | 'qa' | 'eval';

// 测试阶段显示「评分」标签页；交付时置为 false 即可隐藏
const SHOW_EVAL = true;

function App() {
  const [report, setReport] = useState<ReportMeta | null>(null);
  const [summary, setSummary] = useState<StructuredSummary | null>(null);
  const [streamText, setStreamText] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>('summary');
  const [error, setError] = useState('');

  async function handleUploaded(r: ReportMeta) {
    setReport(r);
    setSummary(null);
    setStreamText('');
    setError('');
    setLoading(true);
    try {
      const s = await generateSummaryStream(r.id, (t) =>
        setStreamText((prev) => prev + t),
      );
      setSummary(s);
      setStreamText('');
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
          {report && (
            <div className="text-right text-sm text-gray-500">
              <p className="font-medium text-gray-700">{report.title}</p>
              <p>{report.page_count} 页 · {report.char_count.toLocaleString()} 字</p>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        {!report && <ReportUploader onUploaded={handleUploaded} />}

        {report && (
          <>
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
              {SHOW_EVAL && summary && (
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
                onClick={() => {
                  setReport(null);
                  setSummary(null);
                  setError('');
                  setStreamText('');
                }}
                className="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-white border text-gray-600 hover:bg-gray-50"
              >
                重新上传
              </button>
            </div>

            {loading && (
              <div className="mb-6">
                <div className="text-center mb-3">
                  <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full" />
                  <p className="text-gray-500 mt-2">正在调用 Hy3 生成结构化摘要...</p>
                </div>
                {streamText && (
                  <div>
                    <p className="text-xs text-gray-400 mb-1">模型原始输出（实时）</p>
                    <pre className="bg-gray-900 text-gray-100 text-xs rounded-lg p-4 overflow-auto max-h-80 whitespace-pre-wrap">
                      {streamText}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            {tab === 'summary' && summary && <SummaryView summary={summary} />}
            {tab === 'qa' && <QAChat reportId={report.id} />}
            {tab === 'eval' && summary && (
              <EvalPanel reportId={report.id} summary={summary} />
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
