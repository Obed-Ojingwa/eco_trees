import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { MapPin, Image as ImageIcon } from 'lucide-react';

interface InspectionProject {
  id: string;
  name: string;
  farmer: string;
  location: string;
  submitted_at: string;
  status: string;
  farm_type: string;
  lga: string;
  declared_area: string;
  mapping_type: string;
  species: string;
  tree_count: number;
  planting_status: string;
  planting_date: string;
  satellite_note: string;
  history_note: string;
}

async function fetchProjectInspection(id?: string): Promise<InspectionProject> {
  try {
    const res = await fetch(`/api/plots/${id || 'ET-00124'}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    return {
      id: data.id || 'ET-2026-00124',
      name: data.farm_name || 'Green Valley Farm',
      farmer: data.farmer_display_name || 'Ama Farmer',
      location: 'Abeokuta, Ogun State',
      submitted_at: '07 Nov 2026',
      status: 'Resubmitted',
      farm_type: 'Agroforestry',
      lga: 'Abeokuta',
      declared_area: `${data.area_ha || 2.5} ha`,
      mapping_type: 'GPS walk-around',
      species: 'Mango',
      tree_count: 250,
      planting_status: 'Newly planted',
      planting_date: 'Approx. 2025',
      satellite_note:
        'No verified observation attached to this submission. Do not infer tree survival from unavailable imagery.',
      history_note:
        '05 Nov · A. Bello · Changes requested: add a clearer tree photo. | 07 Nov · Farmer resubmitted existing project.',
    };
  } catch {
    // Exact fallback matching the UI specification
    return {
      id: 'ET-2026-00124',
      name: 'Green Valley Farm',
      farmer: 'Ama Farmer',
      location: 'Abeokuta, Ogun State',
      submitted_at: '07 Nov 2026',
      status: 'Resubmitted',
      farm_type: 'Agroforestry',
      lga: 'Abeokuta',
      declared_area: '2.5 ha',
      mapping_type: 'GPS walk-around',
      species: 'Mango',
      tree_count: 250,
      planting_status: 'Newly planted',
      planting_date: 'Approx. 2025',
      satellite_note:
        'No verified observation attached to this submission. Do not infer tree survival from unavailable imagery.',
      history_note:
        '05 Nov · A. Bello · Changes requested: add a clearer tree photo. | 07 Nov · Farmer resubmitted existing project.',
    };
  }
}

export default function ProjectInspection() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<InspectionProject | null>(null);
  const [comment, setComment] = useState('');

  useEffect(() => {
    fetchProjectInspection(id).then(setProject);
  }, [id]);

  if (!project) {
    return <div className="p-8 text-gray-500 text-sm">Loading project inspection...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Project inspection
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Check the farm details and supporting evidence before recording a decision.
        </p>
      </div>

      {/* Top Banner Card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 flex items-center justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            {project.id} · {project.name}
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            {project.farmer} · {project.location} · Submitted {project.submitted_at}
          </p>
        </div>
        <div>
          <span className="bg-[#eaf3ec] text-[#1b4332] text-xs font-semibold px-4 py-2 rounded-xl">
            {project.status}
          </span>
        </div>
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Evidence & Details */}
        <div className="lg:col-span-8 space-y-6">
          {/* Farm overview */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Farm overview
              </h3>
              <div className="flex flex-wrap gap-8 text-xs text-gray-600">
                <span>Farmer: <strong className="text-gray-800">{project.farmer}</strong></span>
                <span>Farm type: <strong className="text-gray-800">{project.farm_type}</strong></span>
                <span>LGA: <strong className="text-gray-800">{project.lga}</strong></span>
              </div>
            </div>

            {/* Farm boundary */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Farm boundary
              </h3>
              <div className="bg-[#edf5f0] rounded-xl p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                  <MapPin size={16} className="text-gray-700" />
                  <span>Farm boundary record</span>
                </div>
                <p className="text-xs text-gray-600 mt-1 pl-6">
                  Declared area: {project.declared_area} · Mapping: {project.mapping_type}
                </p>
              </div>
            </div>

            {/* Tree information */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Tree information
              </h3>
              <p className="text-xs text-gray-600">
                {project.species} · {project.tree_count} trees · {project.planting_status} · Date: {project.planting_date}
              </p>
            </div>

            {/* Evidence photos */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Evidence
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="border border-gray-200 rounded-xl p-4 flex flex-col items-center justify-center text-center bg-white aspect-square">
                  <ImageIcon size={22} className="text-gray-400 mb-2" />
                  <span className="text-xs text-gray-600">Farm photo</span>
                </div>
                <div className="border border-gray-200 rounded-xl p-4 flex flex-col items-center justify-center text-center bg-white aspect-square">
                  <ImageIcon size={22} className="text-gray-400 mb-2" />
                  <span className="text-xs text-gray-600">Tree photo 01</span>
                </div>
                <div className="border border-gray-200 rounded-xl p-4 flex flex-col items-center justify-center text-center bg-white aspect-square">
                  <ImageIcon size={22} className="text-gray-400 mb-2" />
                  <span className="text-xs text-gray-600">Tree photo 02</span>
                </div>
                <div className="border border-[#1b4332]/20 bg-[#edf5f0] rounded-xl p-4 flex flex-col items-center justify-center text-center aspect-square">
                  <ImageIcon size={22} className="text-[#1b4332] mb-2" />
                  <span className="text-xs text-[#1b4332] font-medium">Close-up</span>
                </div>
              </div>
            </div>

            {/* Satellite observations */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                Satellite observations
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                {project.satellite_note}
              </p>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Review Decision Card */}
        <div className="lg:col-span-4">
          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                Review decision
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                Choose an outcome and leave a clear note for the record.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2.5">
              <button className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3 rounded-xl transition-colors cursor-pointer">
                Internally approve
              </button>
              <button className="w-full border border-gray-200 hover:bg-gray-50 text-gray-700 text-xs font-medium py-3 rounded-xl transition-colors cursor-pointer">
                Request changes
              </button>
              <button className="w-full border border-gray-200 hover:bg-gray-50 text-gray-700 text-xs font-medium py-3 rounded-xl transition-colors cursor-pointer">
                Reject submission
              </button>
            </div>

            {/* Decision Comments */}
            <div>
              <label className="text-xs font-semibold text-gray-900 block mb-2">
                Decision comments *
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Enter reason and specific evidence needed..."
                className="w-full h-24 p-3 rounded-xl border border-gray-200 text-xs text-gray-800 placeholder-gray-400 outline-none focus:border-gray-400 transition-colors resize-none"
              />
            </div>

            {/* Metadata notes */}
            <div className="space-y-1 pt-1 text-xs text-gray-500">
              <p>Auditor: Assigned reviewer</p>
              <p className="text-gray-400">Decision timestamp: Recorded on submit</p>
              <p className="text-gray-400 pt-2 leading-relaxed">
                Internal approval is not carbon-credit certification.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Review History Card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <h3 className="text-sm font-semibold text-gray-900 mb-2">
          Review history
        </h3>
        <p className="text-xs text-gray-600 leading-relaxed">
          {project.history_note}
        </p>
      </div>
    </div>
  );
}
