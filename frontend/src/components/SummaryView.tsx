import type { StructuredSummary } from '../types';

interface Props {
  summary: StructuredSummary;
}

function Section({ title, items, color }: { title: string; items: string[]; color: string }) {
  if (!items.length) return null;
  return (
    <div className="mb-6">
      <h3 className={`font-semibold text-lg mb-2 ${color}`}>{title}</h3>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-gray-700 pl-4 border-l-2 border-gray-200 py-1">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function SummaryView({ summary }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">结构化摘要</h2>

      <Section title="核心结论" items={summary.core_conclusions} color="text-blue-700" />
      <Section title="关键数据" items={summary.key_data} color="text-green-700" />
      <Section title="主要风险" items={summary.main_risks} color="text-red-700" />
      <Section title="投资建议" items={summary.investment_advice} color="text-purple-700" />
      <Section title="需进一步核实的疑点" items={summary.points_to_verify} color="text-amber-700" />

      <div className="mt-6 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
        {summary.disclaimer}
      </div>
    </div>
  );
}
