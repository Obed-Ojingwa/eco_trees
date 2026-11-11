import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Clock } from 'lucide-react';

interface FarmerOverviewStats {
  farms: string;
  trees: string;
  in_review: string;
}

interface RecentFarmProject {
  id: string;
  name: string;
  status: string;
  note: string;
}

interface FarmerOverviewData {
  stats: FarmerOverviewStats;
  recent_project: RecentFarmProject | null;
}

async function fetchFarmerOverview(): Promise<FarmerOverviewData> {
  try {
    const [homeRes, plotsRes] = await Promise.all([
      fetch('/api/farmer/home', { credentials: 'include' }).catch(() => null),
      fetch('/api/plots', { credentials: 'include' }).catch(() => null),
    ]);

    let farmCount = 0;
    let totalTrees = 0;
    let inReviewCount = 0;
    let recentProj: RecentFarmProject | null = null;

    if (plotsRes && plotsRes.ok) {
      const plotsData = await plotsRes.json();
      if (Array.isArray(plotsData.items) && plotsData.items.length > 0) {
        farmCount = plotsData.items.length;
        inReviewCount = plotsData.items.filter(
          (p: { status?: string }) => p.status === 'submitted' || p.status === 'draft'
        ).length;

        // Sum trees
        let trees = 0;
        plotsData.items.forEach((p: { plantings?: { trees_planted?: number }[] }) => {
          if (Array.isArray(p.plantings)) {
            p.plantings.forEach((pl) => {
              trees += pl.trees_planted || 0;
            });
          }
        });
        totalTrees = trees;

        const latest = plotsData.items[0];
        const statusLabel =
          latest.status === 'verified'
            ? 'Internally approved'
            : latest.status === 'submitted'
            ? 'Under review'
            : latest.status === 'draft'
            ? 'Draft'
            : latest.status;

        recentProj = {
          id: `ET-${latest.id.slice(0, 8)}`,
          name: latest.farmer_display_name ? `${latest.farmer_display_name}'s Farm` : 'Farm Project',
          status: statusLabel,
          note:
            latest.status === 'verified'
              ? 'Your farm has been internally verified by EcoTrees.'
              : 'Your submission is with the EcoTrees review team.',
        };
      }
    }

    if (homeRes && homeRes.ok) {
      const homeData = await homeRes.json();
      if (homeData.plot_summary) {
        farmCount = homeData.plot_summary.total || farmCount;
      }
    }

    return {
      stats: {
        farms: String(farmCount).padStart(2, '0'),
        trees: String(totalTrees),
        in_review: String(inReviewCount).padStart(2, '0'),
      },
      recent_project: recentProj,
    };
  } catch {
    // Empty state fallback
    return {
      stats: {
        farms: '00',
        trees: '0',
        in_review: '00',
      },
      recent_project: null,
    };
  }
}

export default function FarmerOverview() {
  const navigate = useNavigate();
  const [data, setData] = useState<FarmerOverviewData | null>(null);

  useEffect(() => {
    fetchFarmerOverview().then(setData);
  }, []);

  if (!data) {
    return <div className="p-8 text-gray-500 text-sm">Loading farm workspace...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-3">
          <span>Good morning, Farmer</span>
          <span className="text-2xl">👋</span>
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Good to have you here. Let’s get your farm set up.
        </p>
      </div>

      {/* Big Action Banner */}
      <div className="bg-[#eaf3ec] rounded-2xl p-8 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[#1b4332]">
            Let’s add your first farm.
          </h2>
          <p className="text-xs text-gray-600 mt-1.5 max-w-md">
            We’ll help you add the location, trees and a few photos.
          </p>

          <button
            onClick={() => navigate('/farmer/register')}
            className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-5 py-3 rounded-xl mt-5 transition-colors cursor-pointer"
          >
            Register a farm
          </button>
        </div>

        <div className="hidden sm:block pr-6">
          <svg
            className="w-16 h-16 text-[#1b4332]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22v-7" />
            <path d="M12 15a5 5 0 0 1-5-5c0-3 2.5-6 5-8 2.5 2 5 5 5 8a5 5 0 0 1-5 5z" />
            <path d="M7 10a4 4 0 0 0-4 4c0 2 1.5 3.5 3.5 3.5" />
            <path d="M17 10a4 4 0 0 1 4 4c0 2-1.5 3.5-3.5 3.5" />
          </svg>
        </div>
      </div>

      {/* Your Farm Overview: 3 Metric Cards */}
      <div className="space-y-4">
        <h3 className="text-base font-semibold text-gray-900">
          Your farm overview
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Farms */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 font-medium">Farms</span>
              <MapPin size={18} className="text-[#1b4332]" />
            </div>
            <div className="text-3xl font-bold text-gray-900 tracking-tight mt-4">
              {data.stats.farms}
            </div>
          </div>

          {/* Trees */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 font-medium">Trees</span>
              <svg
                className="w-4 h-4 text-[#1b4332]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 22v-7" />
                <path d="M12 15a5 5 0 0 1-5-5c0-3 2.5-6 5-8 2.5 2 5 5 5 8a5 5 0 0 1-5 5z" />
              </svg>
            </div>
            <div className="text-3xl font-bold text-gray-900 tracking-tight mt-4">
              {data.stats.trees}
            </div>
          </div>

          {/* In review */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 font-medium">In review</span>
              <Clock size={18} className="text-[#1b4332]" />
            </div>
            <div className="text-3xl font-bold text-gray-900 tracking-tight mt-4">
              {data.stats.in_review}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Project */}
      <div className="space-y-4">
        <h3 className="text-base font-semibold text-gray-900">
          Recent project
        </h3>

        {data.recent_project ? (
          <div
            onClick={() => navigate('/farmer/progress')}
            className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] cursor-pointer hover:border-gray-200 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <MapPin size={18} className="text-[#1b4332]" />
                <span className="font-bold text-base text-gray-900">
                  {data.recent_project.name}
                </span>
              </div>
              <span className="bg-[#fef3c7] text-[#92400e] text-xs font-semibold px-3 py-1 rounded-full">
                {data.recent_project.status}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-3 pl-7">
              {data.recent_project.note}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-8 text-center space-y-2">
            <p className="text-xs text-gray-500">
              No farm projects recorded yet.
            </p>
            <button
              onClick={() => navigate('/farmer/register')}
              className="text-xs font-semibold text-[#1b4332] hover:underline cursor-pointer"
            >
              Register your first farm &rarr;
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
