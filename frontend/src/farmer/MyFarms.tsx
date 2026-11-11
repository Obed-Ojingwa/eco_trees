import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface FarmItem {
  id: string;
  name: string;
  location: string;
  trees: number;
  area_ha: number;
  status: string;
}

async function fetchMyFarms(): Promise<FarmItem[]> {
  try {
    const res = await fetch('/api/plots', { credentials: 'include' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (Array.isArray(data.items) && data.items.length > 0) {
      return data.items.map((p: {
        id: string;
        farmer_display_name?: string;
        area_ha?: number;
        status?: string;
        plantings?: { trees_planted?: number; species_code?: string }[];
      }) => {
        let treeCount = 0;
        if (Array.isArray(p.plantings) && p.plantings.length > 0) {
          treeCount = p.plantings.reduce((sum, pl) => sum + (pl.trees_planted || 0), 0);
        }
        const statusMap: Record<string, string> = {
          draft: 'Draft',
          submitted: 'Under review',
          verified: 'Internally approved',
          flagged: 'Changes requested',
          rejected: 'Rejected',
        };
        const statusStr = statusMap[p.status || ''] || p.status || 'Under review';
        return {
          id: p.id,
          name: p.farmer_display_name ? `${p.farmer_display_name}'s Farm` : 'Farm Project',
          location: 'Ogun State',
          trees: treeCount,
          area_ha: Number(p.area_ha || 0),
          status: statusStr,
        };
      });
    }
    return [];
  } catch {
    return [];
  }
}

export default function MyFarms() {
  const navigate = useNavigate();
  const [farms, setFarms] = useState<FarmItem[]>([]);

  useEffect(() => {
    fetchMyFarms().then(setFarms);
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title & Register Action */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            My farms
          </h1>
          <p className="text-sm text-gray-600 mt-1.5">
            Manage all farms linked to your account.
          </p>
        </div>

        <button
          onClick={() => navigate('/farmer/register')}
          className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-5 py-3 rounded-xl transition-colors cursor-pointer"
        >
          Register another farm
        </button>
      </div>

      {/* Farms List Container */}
      <div className="space-y-4">
        {/* Table Column Labels */}
        <div className="flex items-center justify-between px-6 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
          <span className="w-1/3">Farm</span>
          <span className="w-1/3 text-center">Tree inventory</span>
          <span className="w-1/3 text-right">Status</span>
        </div>

        {/* Farm Cards */}
        <div className="space-y-3">
          {farms.length > 0 ? (
            farms.map((farm) => {
              const isApproved = farm.status.toLowerCase().includes('approved');
              return (
                <div
                  key={farm.id}
                  onClick={() => navigate('/farmer/progress')}
                  className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex items-center justify-between hover:border-gray-200 transition-colors cursor-pointer"
                >
                  {/* Farm Name & Location */}
                  <div className="w-1/3">
                    <h3 className="font-bold text-sm text-gray-900">{farm.name}</h3>
                    <p className="text-xs text-gray-400 mt-1">{farm.location}</p>
                  </div>

                  {/* Tree Inventory */}
                  <div className="w-1/3 text-center">
                    <p className="text-xs text-gray-600">
                      {farm.trees} trees · {farm.area_ha} ha
                    </p>
                  </div>

                  {/* Status & View Link */}
                  <div className="w-1/3 flex items-center justify-end gap-5">
                    <span
                      className={`text-xs font-semibold px-3 py-1 rounded-full ${
                        isApproved
                          ? 'bg-[#eaf3ec] text-[#1b4332]'
                          : 'bg-[#fef3c7] text-[#92400e]'
                      }`}
                    >
                      {farm.status}
                    </span>

                    <span className="text-xs text-gray-700 font-medium flex items-center gap-1 hover:text-[#1b4332]">
                      <span>View farm</span>
                      <ChevronRight size={14} />
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center space-y-3">
              <h4 className="font-bold text-sm text-gray-900">No farms registered yet</h4>
              <p className="text-xs text-gray-400 max-w-sm mx-auto">
                You haven&apos;t registered any restoration plots under this account.
              </p>
              <div className="pt-2">
                <button
                  onClick={() => navigate('/farmer/register')}
                  className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-colors cursor-pointer"
                >
                  Register your first farm
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
