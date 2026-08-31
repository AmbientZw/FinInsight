import { useEffect, useState } from 'react';
import { evaluateSummaryStream } from '../services/api';
import type { EvalDimension, StructuredSummary } from '../types';

interface Props {
  reportId: string;
  summary: StructuredSummary;
}

const DIM_LABELS: Record<string, { name: string; weight: string; kind: string }> = {
  事实准确性: { name: 'D1 事实准确性', weight: '20%', kind: 'LLM' },
  证据可追溯性: { name: 'D2 证据可追溯性', weight: '15%', kind: 'LLM' },
  数据精确性: { name: 'D3 数据精确性', weight: '15%', kind: '规则' },
  信息完整性: { name: 'D4 信息完整性', weight: '15%', kind: 'LLM' },
  结构规范性: { name: 'D5 结构规范性', weight: '10%', kind: '规则' },
  安全合规性: { name: 'D6 安全合规性', weight: '10%', kind: '规则' },
  专业术语正确性: { name: 'D7 专业术语正确性', weight: '15%', kind: 'LLM' },
};

function scoreColor(s: number) {
  if (s >= 4.5) return 'bg-green-500';
  if (s >= 3.5) return 'bg-blue-500';
  if (s >= 2.5) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function EvalPanel({ reportId, summary }: Props) {
  const [dims, setDims] = useState<EvalDimension[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [safetyFlag, setSafetyFlag] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    setDims([]);
    setTotal(null);
    setSafetyFlag(false);
    setError('');
    setRunning(true);
    try {
      await evaluateSummaryStream(
        reportId,
        summary,
        (d) => setDims((prev) => [...prev, d]),
        (r) => {
          setTotal(r.total);
          setSafetyFlag(r.safety_red_flag);
        },
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : '评分失败');
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">评分过程（测试）</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            7 维度混合评测：规则引擎（D3/D5/D6，即时）+ LLM-as-Judge（D1/D2/D4/D7，逐个返回）
          </p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          重新评分
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {dims.map((d) => {
          const meta = DIM_LABELS[d.dimension] ?? {
            name: d.dimension,
            weight: '',
            kind: '',
          };
          return (
            <div key={d.dimension} className="border rounded-lg p-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 w-40 shrink-0">
                  {meta.name}
                </span>
                <span className="text-xs text-gray-400 w-10 shrink-0">{meta.weight}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 shrink-0">
                  {meta.kind}
                </span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${scoreColor(d.score)} transition-all duration-500`}
                    style={{ width: `${(d.score / 5) * 100}%` }}
                  />
                </div>
                <span className="font-bold text-gray-900 w-10 text-right shrink-0">
                  {d.score.toFixed(1)}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-2">{d.reasoning}</p>
              {d.evidence.length > 0 && (
                <ul className="mt-1 text-xs text-gray-400 list-disc pl-4 space-y-0.5">
                  {d.evidence.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {running && (
        <div className="flex items-center gap-2 text-gray-500 mt-4">
          <div className="animate-spin w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full" />
          正在评分（LLM 维度逐个返回）...
        </div>
      )}

      {total !== null && (
        <div
          className={`mt-4 p-4 rounded-lg ${
            safetyFlag
              ? 'bg-red-50 border border-red-200'
              : 'bg-blue-50 border border-blue-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-gray-800">加权总分</span>
            <span className="text-2xl font-bold text-gray-900">
              {total.toFixed(2)} / 5.00
            </span>
          </div>
          {safetyFlag && (
            <p className="text-red-700 text-sm mt-1">⚠️ 触发安全红线（检测到越界承诺）</p>
          )}
        </div>
      )}
    </div>
  );
}
