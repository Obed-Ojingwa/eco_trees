import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronDown, MapPin, Info } from 'lucide-react';

interface MarketplaceProject {
  id: string;
  name: string;
  location: string;
  trees: number;
  area_ha: number;
  status: string;
}

async function fetchMarketplaceProjects(): Promise<MarketplaceProject[]> {
  try {
    const [creditsRes, plotsRes] = await Promise.all([
      fetch('/api/marketplace/credits', { credentials: 'include' }).catch(() => null),
      fetch('/api/plots', { credentials: 'include' }).catch(() => null),
    ]);

    if (creditsRes && creditsRes.ok) {
      const data = await creditsRes.json();
      if (Array.isArray(data.items) && data.items.length > 0) {
        return data.items.map((c: {
          serial: string;
          price_per_tonne_kobo?: number;
          batch_number?: string;
          vintage?: number;
        }) => ({
          id: c.serial,
          name: `Batch ${c.batch_number || '01'} (${c.vintage || 2026})`,
          location: 'Nigeria · Registered Project',
          trees: 250,
          area_ha: 2.5,
          status: 'Internally approved · Demo marketplace',
        }));
      }
    }

    if (plotsRes && plotsRes.ok) {
      const data = await plotsRes.json();
      if (Array.isArray(data.items) && data.items.length > 0) {
        return data.items.map((p: {
          id: string;
          farmer_display_name?: string;
          area_ha?: number;
          plantings?: { trees_planted?: number }[];
        }) => {
          let trees = 250;
          if (Array.isArray(p.plantings) && p.plantings.length > 0) {
            trees = p.plantings.reduce((sum, pl) => sum + (pl.trees_planted || 0), 0) || 250;
          }
          return {
            id: p.id,
            name: p.farmer_display_name ? `${p.farmer_display_name}'s Farm` : 'Green Valley Farm',
            location: 'Abeokuta, Ogun State',
            trees,
            area_ha: Number(p.area_ha || 2.5),
            status: 'Internally approved · Demo marketplace',
          };
        });
      }
    }
    return [];
  } catch {
    return [];
  }
}

export default function ExploreProjects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<MarketplaceProject[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchMarketplaceProjects().then(setProjects);
  }, []);

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.location.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Page Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Explore nature-based projects
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Explore farm projects, see the information behind them and understand what each demo listing includes.
        </p>
      </div>

      {/* Filter Row: 4 Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {/* Search */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Search project or location
          </label>
          <div className="flex items-center justify-between">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="All"
              className="text-xs text-gray-800 placeholder-gray-400 bg-transparent outline-none w-full"
            />
            <Search size={14} className="text-gray-400 shrink-0 ml-1" />
          </div>
        </div>

        {/* State */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            State
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* Farm type */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Farm type
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>

        {/* Sort */}
        <div className="bg-white rounded-2xl border border-gray-100 p-3.5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <label className="text-[11px] font-medium text-gray-500 block mb-1">
            Sort: Recently updated
          </label>
          <div className="flex items-center justify-between text-xs text-gray-800 cursor-pointer">
            <span>All</span>
            <ChevronDown size={14} className="text-gray-400" />
          </div>
        </div>
      </div>

      {/* Projects Grid: 3 Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {filtered.length > 0 ? (
          filtered.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-2xl border border-gray-100 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between"
            >
              <div>
                {/* Top Illustration Area */}
                <div className="bg-[#eaf3ec] rounded-xl h-36 flex flex-col items-center justify-center mb-4">
                  <svg
                    className="w-10 h-10 text-[#1b4332]"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 22v-7" />
                    <path d="M12 15a5 5 0 0 1-5-5c0-3 2.5-6 5-8 2.5 2 5 5 5 8a5 5 0 0 1-5 5z" />
                    <path d="M7 10a4 4 0 0 0-4 4c0 2 1.5 3.5 3.5 3.5" />
                    <path d="M17 10a4 4 0 0 1 4 4c0 2-1.5 3.5-3.5 3.5" />
                  </svg>
                  <span className="text-[11px] text-gray-500 mt-2 font-medium">
                    Farm project
                  </span>
                </div>

                {/* Title & Location */}
                <h3 className="font-bold text-base text-gray-900">{item.name}</h3>
                <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-1">
                  <MapPin size={13} className="text-gray-400 shrink-0" />
                  <span>{item.location}</span>
                </div>

                {/* Trees & Area */}
                <p className="text-xs text-gray-600 mt-3 font-normal">
                  {item.trees} trees · {item.area_ha} ha
                </p>

                {/* Status */}
                <p className="text-xs text-[#1b4332] font-semibold mt-3">
                  {item.status}
                </p>
              </div>

              {/* Action Button */}
              <div className="pt-5">
                <button
                  onClick={() => navigate(`/buyer/project/${item.id}`)}
                  className="w-full border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold py-2.5 rounded-xl transition-colors cursor-pointer"
                >
                  View project
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="md:col-span-3 bg-white rounded-2xl border border-dashed border-gray-200 p-14 text-center space-y-3">
            <h3 className="font-bold text-base text-gray-900">No projects currently listed</h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto leading-relaxed">
              When nature-based restoration projects are internally approved and listed, they will appear here.
            </p>
          </div>
        )}
      </div>

      {/* Important Marketplace Notice Banner */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1.5">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Important marketplace notice</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          These are EcoTrees demo marketplace project units based on internally reviewed records. They are not certified carbon credits and do not represent formal issuance.
        </p>
      </div>
    </div>
  );
}
