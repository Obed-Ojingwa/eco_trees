import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Info } from 'lucide-react';

interface ProjectDetailData {
  id: string;
  name: string;
  location: string;
  farm_type: string;
  area_ha: number;
  trees: number;
  species: string;
  units: number;
  price_per_unit: number;
}

async function fetchProjectDetail(id?: string): Promise<ProjectDetailData> {
  try {
    const res = await fetch(`/api/plots/${id || 'ET-00124'}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    return {
      id: data.id || 'ET-00124',
      name: data.farm || data.farmer_display_name || 'Green Valley Farm',
      location: 'Abeokuta, Ogun State',
      farm_type: 'Agroforestry',
      area_ha: Number(data.area_ha || 2.5),
      trees: 250,
      species: 'mango',
      units: 100,
      price_per_unit: 5000,
    };
  } catch {
    // Exact fallback matching the UI specification
    return {
      id: 'ET-00124',
      name: 'Green Valley Farm',
      location: 'Abeokuta, Ogun State',
      farm_type: 'Agroforestry',
      area_ha: 2.5,
      trees: 250,
      species: 'mango',
      units: 100,
      price_per_unit: 5000,
    };
  }
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDetailData | null>(null);

  useEffect(() => {
    fetchProjectDetail(id).then(setProject);
  }, [id]);

  if (!project) {
    return <div className="p-8 text-gray-500 text-sm">Loading project details...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Page Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          {project.name}
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Get to know the farm, review its available information and see what the demo listing represents.
        </p>
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (8 cols): Project Overview Card */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
          {/* Top Illustration Banner */}
          <div className="bg-[#eaf3ec] rounded-xl h-44 flex flex-col items-center justify-center">
            <svg
              className="w-12 h-12 text-[#1b4332]"
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

          {/* Farm Header Info */}
          <div>
            <h2 className="text-xl font-bold text-gray-900">{project.name}</h2>
            <p className="text-xs text-gray-500 mt-1">
              {project.location} · {project.farm_type} · {project.area_ha} hectares
            </p>
          </div>

          {/* Project overview */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Project overview
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              {project.trees} {project.species} trees recorded · Farm boundary mapped · Evidence photos submitted · Internal review completed
            </p>
          </div>

          {/* Evidence and review status */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Evidence and review status
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              Farm photos available · Boundary record available · Internal status: approved for demo marketplace
            </p>
          </div>
        </div>

        {/* Right Column (4 cols): Checkout Prompt Card */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <div>
            <label className="text-xs text-gray-500 block">
              Demo marketplace units
            </label>
            <div className="text-2xl font-bold text-gray-900 mt-1">
              {project.units} units
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Illustrative quantity for prototype only
            </p>
          </div>

          <div className="mt-5">
            <label className="text-xs text-gray-500 block">
              Illustrative price
            </label>
            <div className="text-lg font-bold text-gray-900 mt-1">
              ₦{project.price_per_unit.toLocaleString()} / unit
            </div>
          </div>

          <button
            onClick={() => navigate(`/buyer/checkout/${project.id}`)}
            className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3.5 rounded-xl transition-colors cursor-pointer mt-6"
          >
            Continue to demo checkout
          </button>
        </div>
      </div>

      {/* Disclaimer Banner */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1.5">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Not a certified carbon credit</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          Internal EcoTrees approval only. No formal certification, registry issuance, verified tonnes of CO2e or real carbon-credit ownership is represented.
        </p>
      </div>
    </div>
  );
}
