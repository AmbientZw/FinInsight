import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Chart } from '../types';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#14b8a6'];

function renderChart(chart: Chart) {
  switch (chart.chart_type) {
    case 'line':
      return (
        <LineChart data={chart.data} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
        </LineChart>
      );
    case 'pie':
      return (
        <PieChart>
          <Pie data={chart.data} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={90} label>
            {chart.data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      );
    case 'bar':
    default:
      return (
        <BarChart data={chart.data} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={48} />
        </BarChart>
      );
  }
}

export default function ChartsView({ charts }: { charts: Chart[] }) {
  if (!charts || charts.length === 0) return null;

  return (
    <div className="mb-6">
      <h3 className="font-semibold text-lg mb-3 text-sky-700">数据图表</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {charts.map((chart, i) => (
          <div key={i} className="border border-gray-100 rounded-lg p-4 bg-gray-50/60">
            <p className="text-sm font-medium text-gray-700 mb-2">
              {chart.title}
              {chart.unit && (
                <span className="text-xs text-gray-400 ml-1">（单位：{chart.unit}）</span>
              )}
            </p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                {renderChart(chart)}
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
