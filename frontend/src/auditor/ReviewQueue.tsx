import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronDown } from 'lucide-react';
import DemoDataNotice from '../shared/DemoDataNotice';
import { DEMO_FARM_PROJECTS } from '../shared/demoData';

interface ReviewQueueItem {
  id: string;
  displayId?: string;
  farm: string;
  farmer: string;
  location: string;
  submitted_at: string;
  status: string;
  priority: string;
  isDemo?: boolean;
}

const demoQueue: ReviewQueueItem[] = DEMO_FARM_PROJECTS
  .filter((project) => project.status !== 'Internally approved')
  .map((project) => ({
    id: project.id,
    displayId: project.id,
    farm: project.farm,
    farmer: project.farmer,
    location: project.location,
    submitted_at: project.submittedAt,
    status: project.status,
    priority: project.priority,
    isDemo: true,
  }));

async function fetchReviewQueue(): Promise<ReviewQueueItem[]> {
  try {
    const res = await fetch('/api/plots', { credentials: 'include' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (Array.isArray(data.items) && data.items.length > 0) {
      return data.items.map((p: {
        id: string;
        farmer_display_name?: string;
        created_at?: string;
        status?: string;
        flags?: string[];
      }) => {
        const statusMap: Record<string, string> = {
          submitted: 'Awaiting review',
          verified: 'Internally approved',
          flagged: 'Changes requested',
          rejected: 'Rejected',
          draft: 'Draft',
        };
        const dateStr = p.created_at
          ? new Date(p.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
          : 'Today';
        const hasFlag = Array.isArray(p.flags) && p.flags.length > 0;
        return {
          id: p.id,
          displayId: `ET-${p.id.slice(0, 5)}`,
          farm: p.farmer_display_name ? `${p.farmer_display_name}'s Farm` : 'Farm Project',
          farmer: p.farmer_display_name || 'Assigned Farmer',
          location: 'Abeokuta, Ogun',
          submitted_at: dateStr,
          status: statusMap[p.status || ''] || 'Awaiting review',
          priority: hasFlag ? 'High' : 'Normal',
        };
      });
    }
    return [];
  } catch {
    return [];
  }
}

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ReviewQueueItem[]>(demoQueue);
  const [usingDemoData, setUsingDemoData] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchReviewQueue().then((liveItems) => {
      setUsingDemoData(liveItems.length === 0);
      setItems(liveItems.length > 0 ? liveItems : demoQueue);
    });
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

      {usingDemoData && <DemoDataNotice />}

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
              {filteredItems.length > 0 ? (
                filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-[#fafbfa] transition-colors">
                    <td className="py-4 px-5 font-semibold text-gray-900">{item.displayId || item.id}</td>
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
                      {item.isDemo ? (
                        <span className="text-gray-400">Sample only</span>
                      ) : (
                        <button
                          onClick={() => navigate(`/auditor/project-inspection/${item.id}`)}
                          className="text-gray-800 hover:text-[#1b4332] font-medium cursor-pointer transition-colors"
                        >
                          Open review
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-14 text-center text-xs text-gray-400">
                    No farm submissions found in the review queue.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer: Pagination */}
        <div className="p-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <span>
            {filteredItems.length > 0
              ? `Showing 1–${filteredItems.length} of ${filteredItems.length} projects`
              : 'Showing 0 projects'}
          </span>
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
