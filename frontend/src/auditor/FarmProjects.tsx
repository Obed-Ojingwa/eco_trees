import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronDown, MapPin } from 'lucide-react';

interface FarmProjectItem {
  id: string;
  farm: string;
  farmer: string;
  state: string;
  status: string;
  isApproved?: boolean;
}

async function fetchFarmProjects(): Promise<FarmProjectItem[]> {
  try {
    const res = await fetch('/api/plots', { credentials: 'include' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (Array.isArray(data.items) && data.items.length > 0) {
      return data.items.map((p: {
        id: string;
        farmer_display_name?: string;
        status?: string;
      }) => {
        const statusMap: Record<string, string> = {
          submitted: 'Awaiting review',
          verified: 'Internally approved',
          flagged: 'Changes requested',
          rejected: 'Rejected',
          draft: 'Draft',
        };
        const status = statusMap[p.status || ''] || p.status || 'Awaiting review';
        return {
          id: `ET-${p.id.slice(0, 5)}`,
          farm: p.farmer_display_name ? `${p.farmer_display_name}'s Farm` : 'Farm Project',
          farmer: p.farmer_display_name || 'Assigned Farmer',
          state: 'Ogun',
          status,
          isApproved: status.toLowerCase().includes('approved'),
        };
      });
    }
    return [];
  } catch {
    return [];
  }
}

export default function FarmProjects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<FarmProjectItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchFarmProjects().then(setProjects);
  }, []);

  const filteredProjects = projects.filter(
    (p) =>
      p.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.farm.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.farmer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Farm projects
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Find a project, check its current status or open its review.
        </p>
      </div>

      {/* Filter Row: 4 Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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

        {/* Farm type */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Farm type
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>
      </div>

      {/* Main List Container */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
        {filteredProjects.length > 0 ? (
          filteredProjects.map((p) => {
            const isGreen = p.isApproved;
            return (
              <div
                key={p.id}
                onClick={() => navigate(`/auditor/project-inspection/${p.id}`)}
                className={`rounded-xl px-5 py-4 flex items-center text-xs cursor-pointer transition-colors ${
                  isGreen
                    ? 'bg-[#f0f7f2] text-[#1b4332] hover:bg-[#e6f2e9]'
                    : 'bg-[#f8faf8] text-gray-700 hover:bg-gray-100/70'
                }`}
              >
                <MapPin
                  size={16}
                  className={`mr-3 shrink-0 ${isGreen ? 'text-[#1b4332]' : 'text-gray-500'}`}
                />
                <span className={`font-semibold mr-2 ${isGreen ? 'text-[#1b4332]' : 'text-gray-900'}`}>
                  {p.id}
                </span>
                <span className="font-medium">{p.farm}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span>{p.farmer}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span>{p.state}</span>
                <span className="mx-2 text-gray-400">·</span>
                <span className={isGreen ? 'font-semibold text-[#1b4332]' : 'text-gray-600'}>
                  {p.status}
                </span>
              </div>
            );
          })
        ) : (
          <div className="py-14 text-center text-xs text-gray-400">
            No farm projects registered yet.
          </div>
        )}
      </div>
    </div>
  );
}
