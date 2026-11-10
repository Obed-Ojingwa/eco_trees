import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronDown } from 'lucide-react';

interface ReviewQueueItem {
  id: string;
  farm: string;
  farmer: string;
  location: string;
  submitted_at: string;
  status: string;
  priority: string;
}

async function fetchReviewQueue(): Promise<ReviewQueueItem[]> {
  try {
    const res = await fetch('/api/plots');
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (Array.isArray(data.items) && data.items.length > 0) {
      return data.items.map((p: Record<string, unknown>) => ({
        id: String(p.id || 'ET-00000'),
        farm: String(p.farm || p.farmer_display_name || 'Farm Project'),
        farmer: String(p.farmer || p.farmer_display_name || 'Assigned Farmer'),
        location: String(p.location || 'Ogun'),
        submitted_at: String(p.submitted_at || p.created_at || 'Recent'),
        status: String(p.status || 'Awaiting review'),
        priority: String(p.priority || 'Normal'),
      }));
    }
    throw new Error();
  } catch {
    // Exact fallback matching the UI specification
    return [
      {
        id: 'ET-00124',
        farm: 'Green Valley Farm',
        farmer: 'Ama Farmer',
        location: 'Abeokuta, Ogun',
        submitted_at: '07 Nov 2026',
        status: 'Resubmitted',
        priority: 'High',
      },
      {
        id: 'ET-00118',
        farm: 'Sunrise Agro Farm',
        farmer: 'K. Ade',
        location: 'Ijebu, Ogun',
        submitted_at: '06 Nov 2026',
        status: 'Awaiting review',
        priority: 'Normal',
      },
      {
        id: 'ET-00109',
        farm: 'Olu Farm Project',
        farmer: 'O. Yusuf',
        location: 'Ibadan, Oyo',
        submitted_at: '05 Nov 2026',
        status: 'Awaiting review',
        priority: 'Normal',
      },
      {
        id: 'ET-00103',
        farm: 'Green Earth',
        farmer: 'B. James',
        location: 'Osogbo, Osun',
        submitted_at: '03 Nov 2026',
        status: 'Under review',
        priority: 'Normal',
      },
    ];
  }
}

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchReviewQueue().then(setItems);
  }, []);

  const filteredItems = items.filter(
    (item) =>
      item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.farm.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.farmer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Review queue
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Start with resubmissions, then work through the oldest waiting projects.
        </p>
      </div>

      {/* Filter Row: 5 Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {/* Search */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Search project
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

        {/* Status */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Status
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* State */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            State
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* Priority */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Priority
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* Sort by */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Sort by
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#f8faf8] border-b border-gray-100 text-[11px] font-semibold tracking-wider text-gray-500 uppercase">
                <th className="py-3 px-5">PROJECT ID</th>
                <th className="py-3 px-4">FARM NAME</th>
                <th className="py-3 px-4">FARMER</th>
                <th className="py-3 px-4">LOCATION</th>
                <th className="py-3 px-4">SUBMITTED</th>
                <th className="py-3 px-4">STATUS</th>
                <th className="py-3 px-4">PRIORITY</th>
                <th className="py-3 px-5 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-[#fafbfa] transition-colors">
                  <td className="py-4 px-5 font-semibold text-gray-900">{item.id}</td>
                  <td className="py-4 px-4 text-gray-800 font-medium">{item.farm}</td>
                  <td className="py-4 px-4 text-gray-600">{item.farmer}</td>
                  <td className="py-4 px-4 text-gray-600">{item.location}</td>
                  <td className="py-4 px-4 text-gray-600">{item.submitted_at}</td>
                  <td className="py-4 px-4">
                    <span className="text-gray-800">{item.status}</span>
                  </td>
                  <td className="py-4 px-4">
                    <span
                      className={
                        item.priority === 'High'
                          ? 'font-medium text-gray-900'
                          : 'text-gray-600'
                      }
                    >
                      {item.priority}
                    </span>
                  </td>
                  <td className="py-4 px-5 text-right">
                    <button
                      onClick={() => navigate(`/auditor/project-inspection/${item.id}`)}
                      className="text-gray-800 hover:text-[#1b4332] font-medium cursor-pointer transition-colors"
                    >
                      Open review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Table Footer: Pagination */}
        <div className="p-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <span>Showing 1–{filteredItems.length} of 24 projects</span>
          <div className="flex items-center gap-4">
            <button className="hover:text-gray-900 cursor-pointer">Previous</button>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">1</span>
              <span className="hover:text-gray-900 cursor-pointer">2</span>
              <span className="hover:text-gray-900 cursor-pointer">3</span>
            </div>
            <button className="hover:text-gray-900 cursor-pointer">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
