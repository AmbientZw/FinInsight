import { useState, useRef } from 'react';
import type { ReportMeta } from '../types';
import { uploadReport } from '../services/api';

interface Props {
  onUploaded: (report: ReportMeta) => void;
}

export default function ReportUploader({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('仅支持 PDF 文件');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const report = await uploadReport(file);
      onUploaded(report);
    } catch (e: any) {
      setError(e.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => inputRef.current?.click()}
      className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-colors"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />

      {uploading ? (
        <div className="text-gray-500">
          <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full mb-3" />
          <p>正在上传并解析...</p>
        </div>
      ) : (
        <div>
          <p className="text-lg font-medium text-gray-700 mb-2">
            点击或拖拽上传研报 PDF
          </p>
          <p className="text-sm text-gray-400">支持行业研报、上市公司年报等</p>
        </div>
      )}

      {error && <p className="text-red-500 mt-3 text-sm">{error}</p>}
    </div>
  );
}
