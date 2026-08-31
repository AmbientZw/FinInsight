import { useState } from 'react';
import { askQuestionStream, DISCLAIMER } from '../services/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  reportId: string;
}

export default function QAChat({ reportId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
    setLoading(true);

    try {
      const answer = await askQuestionStream(reportId, question, (t) => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + t };
          return copy;
        });
      });
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { ...last, content: answer + '\n\n' + DISCLAIMER };
        return copy;
      });
    } catch {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.role === 'assistant') {
          copy[copy.length - 1] = {
            ...last,
            content: last.content ? last.content + '\n\n[生成中断]' : '请求失败，请重试。',
          };
        } else {
          copy.push({ role: 'assistant', content: '请求失败，请重试。' });
        }
        return copy;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border flex flex-col h-[500px]">
      <div className="p-4 border-b">
        <h2 className="text-lg font-bold text-gray-900">研报问答</h2>
        <p className="text-sm text-gray-400">基于上传的研报内容回答问题</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-gray-400 text-center mt-12">
            输入问题开始对话，例如："这份报告的核心增长驱动力是什么？"
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg max-w-[85%] whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'ml-auto bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && messages[messages.length - 1]?.content === '' && (
          <div className="bg-gray-100 p-3 rounded-lg max-w-[85%]">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="输入你的问题..."
          className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-blue-500 text-white px-5 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          发送
        </button>
      </div>
    </div>
  );
}
