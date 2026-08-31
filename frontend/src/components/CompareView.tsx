import { useState } from 'react';
import { compareReportsStream, DISCLAIMER } from '../services/api';
import type { ReportMeta, StructuredSummary } from '../types';

export interface CompareEntry {
  meta: ReportMeta;
  summary: StructuredSummary;
}

interface Props {
  reports: CompareEntry[];
}

export default function CompareView({ reports }: Props) {
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleCompare() {
    if (loading) return;
    setLoading(true);
    setResult('');
    setError('');
    try {
      const text = await compareReportsStream(
        reports.map((r) => ({
          title: r.meta.title ?? r.meta.filename,
          summary: r.summary,
        })),
        (t) => setResult((prev) => prev + t),
      );
      setResult(text + '\n\n' + DISCLAIMER);
    } catch (e) {
      setError(e instanceof Error ? e.message : '对比失败，请重试');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">多报告对比</h2>
          <p className="text-sm text-gray-400">
            对已上传的 {reports.length} 份报告做交叉对比与矛盾检测
          </p>
        </div>
        <button
          onClick={handleCompare}
          disabled={loading || reports.length < 2}
          className="bg-blue-500 text-white px-5 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          {loading ? '对比中...' : '开始对比'}
        </button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {reports.map((r) => (
          <span
            key={r.meta.id}
            className="text-xs bg-gray-100 border border-gray-200 text-gray-600 px-3 py-1 rounded-full"
          >
            {r.meta.title ?? r.meta.filename}
          </span>
        ))}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
          {error}
        </div>
      )}

      {loading && !result && (
        <div className="flex items-center gap-3 text-gray-500 py-8">
          <div className="animate-spin inline-block w-6 h-6 border-4 border-blue-400 border-t-transparent rounded-full" />
          <span>正在调用 Hy3 对比分析...</span>
        </div>
      )}

      {result && (
        <div className="bg-gray-50 rounded-lg p-5 whitespace-pre-wrap text-gray-800 text-sm leading-relaxed">
          {result}
        </div>
      )}
    </div>
  );
}
