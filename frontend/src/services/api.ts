import axios from 'axios';
import type {
  ReportMeta,
  StructuredSummary,
  QAResponse,
  EvalDimension,
  CompareReportInput,
} from '../types';

const api = axios.create({ baseURL: '/api' });

export const DISCLAIMER =
  '⚠️ 免责声明：本分析由AI模型自动生成，仅供参考，不构成任何投资建议。投资有风险，决策需谨慎。请结合专业判断使用。';

export async function uploadReport(file: File): Promise<ReportMeta> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<ReportMeta>('/reports/upload', form);
  return data;
}

export async function listReports(): Promise<ReportMeta[]> {
  const { data } = await api.get<ReportMeta[]>('/reports/');
  return data;
}

export async function generateSummary(reportId: string): Promise<StructuredSummary> {
  const { data } = await api.post<StructuredSummary>(`/summary/${reportId}`);
  return data;
}

export async function askQuestion(
  reportId: string,
  question: string,
): Promise<QAResponse> {
  const { data } = await api.post<QAResponse>('/qa/', {
    report_id: reportId,
    question,
    reasoning_effort: 'high',
  });
  return data;
}

// ===== 流式输出（SSE） =====

async function consumeSSE(
  url: string,
  init: RequestInit,
  onEvent: (payload: unknown) => void,
): Promise<string> {
  const res = await fetch(url, init);
  if (!res.ok || !res.body) {
    let msg = '';
    try {
      msg = await res.text();
    } catch {
      /* ignore */
    }
    throw new Error(`请求失败 (HTTP ${res.status})${msg ? '：' + msg : ''}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let full = '';

  const handleEvent = (event: string) => {
    for (const line of event.split('\n')) {
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim();
      if (!raw) continue;
      if (raw === '[DONE]') continue;
      if (raw.startsWith('[ERROR]')) {
        let msg = raw.slice(8).trim();
        try {
          msg = JSON.parse(msg);
        } catch {
          /* keep raw */
        }
        throw new Error(String(msg));
      }
      let payload: unknown = raw;
      try {
        payload = JSON.parse(raw);
      } catch {
        /* 后端未做 JSON 编码时保留原文 */
      }
      if (typeof payload === 'string') full += payload;
      onEvent(payload);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const event = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      handleEvent(event);
    }
  }
  buffer += decoder.decode();
  if (buffer.trim()) handleEvent(buffer);

  return full;
}

export function parseSummary(raw: string): StructuredSummary {
  try {
    let cleaned = raw.trim();
    if (cleaned.startsWith('```')) {
      cleaned = cleaned.split('\n').slice(1).join('\n');
      if (cleaned.includes('```')) cleaned = cleaned.split('```')[0];
    }
    const data = JSON.parse(cleaned);
    return {
      core_conclusions: data.core_conclusions ?? [],
      key_data: data.key_data ?? [],
      main_risks: data.main_risks ?? [],
      investment_advice: data.investment_advice ?? [],
      points_to_verify: data.points_to_verify ?? [],
      disclaimer: data.disclaimer ?? DISCLAIMER,
      charts: Array.isArray(data.charts) ? data.charts : [],
    };
  } catch {
    return {
      core_conclusions: [raw.slice(0, 500)],
      key_data: [],
      main_risks: [],
      investment_advice: [],
      points_to_verify: ['JSON解析失败，请检查模型输出格式'],
      disclaimer: DISCLAIMER,
      charts: [],
    };
  }
}

export async function generateSummaryStream(
  reportId: string,
  onDelta: (text: string) => void,
): Promise<StructuredSummary> {
  let verifyFlags: string[] = [];
  const raw = await consumeSSE(
    `/api/summary/${reportId}/stream`,
    { method: 'POST' },
    (p) => {
      if (typeof p === 'string') {
        onDelta(p);
      } else if (
        p &&
        typeof p === 'object' &&
        'verify' in p &&
        Array.isArray((p as { verify: unknown }).verify)
      ) {
        verifyFlags = (p as { verify: string[] }).verify;
      }
    },
  );
  const summary = parseSummary(raw);
  if (verifyFlags.length > 0) {
    summary.points_to_verify = [...summary.points_to_verify, ...verifyFlags];
  }
  return summary;
}

export async function askQuestionStream(
  reportId: string,
  question: string,
  onDelta: (text: string) => void,
): Promise<string> {
  return consumeSSE(
    '/api/qa/stream',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id: reportId, question, reasoning_effort: 'high' }),
    },
    (p) => {
      if (typeof p === 'string') onDelta(p);
    },
  );
}

export async function compareReportsStream(
  reports: CompareReportInput[],
  onDelta: (text: string) => void,
): Promise<string> {
  return consumeSSE(
    '/api/compare/stream',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reports }),
    },
    (p) => {
      if (typeof p === 'string') onDelta(p);
    },
  );
}

export async function evaluateSummaryStream(
  reportId: string,
  summary: StructuredSummary,
  onDimension: (d: EvalDimension) => void,
  onDone: (r: { total: number; safety_red_flag: boolean }) => void,
): Promise<void> {
  await consumeSSE(
    `/api/eval/${reportId}/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(summary),
    },
    (p) => {
      if (p && typeof p === 'object') {
        const obj = p as Record<string, unknown>;
        if (obj.done === true) {
          onDone({
            total: Number(obj.total ?? 0),
            safety_red_flag: Boolean(obj.safety_red_flag),
          });
        } else if (typeof obj.dimension === 'string') {
          onDimension({
            dimension: obj.dimension,
            weight: Number(obj.weight ?? 0),
            score: Number(obj.score ?? 0),
            reasoning: String(obj.reasoning ?? ''),
            evidence: Array.isArray(obj.evidence) ? (obj.evidence as string[]) : [],
          });
        }
      }
    },
  );
}
