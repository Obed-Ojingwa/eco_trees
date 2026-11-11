import { useEffect, useState } from 'react';
import { Search, ChevronDown, Clock } from 'lucide-react';

interface HistoryItem {
  id: string;
  date: string;
  time: string;
  reviewer: string;
  project_id: string;
  action: string;
  isApproved?: boolean;
}

async function fetchReviewHistory(): Promise<HistoryItem[]> {
  try {
    const res = await fetch('/api/plots', { credentials: 'include' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (Array.isArray(data.items) && data.items.length > 0) {
      return data.items.map((p: { id: string; status?: string; updated_at?: string; created_at?: string }, idx: number) => {
        const statusMap: Record<string, string> = {
          submitted: 'Awaiting review',
          verified: 'Internally approved',
          flagged: 'Changes requested',
          rejected: 'Rejected',
          draft: 'Draft created',
        };
        const action = statusMap[p.status || ''] || p.status || 'Reviewed';
        const dateObj = new Date(p.updated_at || p.created_at || Date.now());
        return {
          id: String(p.id || idx),
          date: dateObj.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
          time: dateObj.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
          reviewer: 'Auditor Reviewer',
          project_id: `Project ET-${p.id.slice(0, 5)}`,
          action,
          isApproved: action.toLowerCase().includes('approved'),
        };
      });
    }
    return [];
  } catch {
    return [];
  }
}

export default function ReviewHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchReviewHistory().then(setHistory);
  }, []);

  const filteredHistory = history.filter(
    (h) =>
      h.project_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.reviewer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.action.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Review history
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          See who reviewed each project, what they decided and when.
        </p>
      </div>

      {/* Filter Row: 3 Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Search */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Search history
          </label>
          <div className="flex items-center justify-between">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search..."
              className="text-xs text-gray-800 placeholder-gray-400 bg-transparent outline-none w-full"
            />
            <Search size={14} className="text-gray-400 shrink-0 ml-1" />
          </div>
        </div>

        {/* Reviewer */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Reviewer
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* Decision */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Decision
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>
      </div>

      {/* Main List Container */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
        {filteredHistory.length > 0 ? (
          filteredHistory.map((item) => {
            const isGreen = item.isApproved;
            return (
              <div
                key={item.id}
                className={`rounded-xl px-5 py-4 flex items-center text-xs transition-colors ${
                  isGreen
                    ? 'bg-[#f0f7f2] text-[#1b4332]'
                    : 'bg-[#f8faf8] text-gray-700'
                }`}
              >
                <Clock
                  size={16}
                  className={`mr-3 shrink-0 ${isGreen ? 'text-[#1b4332]' : 'text-gray-500'}`}
                />
                <span>{item.date}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span>{item.time}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span className="font-medium">{item.reviewer}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span className="font-semibold">{item.project_id}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span className={isGreen ? 'font-semibold text-[#1b4332]' : 'text-gray-600'}>
                  {item.action}
                </span>
              </div>
            );
          })
        ) : (
          <div className="py-14 text-center text-xs text-gray-400">
            No audit review history recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}
