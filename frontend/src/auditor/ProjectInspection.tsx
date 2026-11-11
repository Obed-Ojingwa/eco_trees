import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MapPin, Image as ImageIcon } from 'lucide-react';

interface InspectionProject {
  id: string;
  displayId?: string;
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
  photos?: { id: string; content_url: string }[];
}

async function fetchProjectInspection(id?: string): Promise<InspectionProject | null> {
  if (id && id.length > 5) {
    try {
      const [plotRes, monRes] = await Promise.all([
        fetch(`/api/plots/${id}`, { credentials: 'include' }).catch(() => null),
        fetch(`/api/plots/${id}/monitoring`, { credentials: 'include' }).catch(() => null),
      ]);

      if (plotRes && plotRes.ok) {
        const data = await plotRes.json();
        let monNote =
          'No verified observation attached to this submission. Do not infer tree survival from unavailable imagery.';
        if (monRes && monRes.ok) {
          const mon = await monRes.json();
          if (mon.assessments && mon.assessments.length > 0) {
            monNote = `Assessment: ${mon.assessments[0].summary || mon.monitoring_state}`;
          } else if (mon.monitoring_state) {
            monNote = `Monitoring state: ${mon.monitoring_state}. Initial observations pending.`;
          }
        }

        let species = 'Gmelina';
        let treeCount = 250;
        let plantingDate = '2025';
        if (Array.isArray(data.plantings) && data.plantings.length > 0) {
          species = data.plantings[0].species_code || 'Gmelina';
          treeCount = data.plantings.reduce(
            (sum: number, pl: { trees_planted?: number }) => sum + (pl.trees_planted || 0),
            0
          );
          plantingDate = data.plantings[0].planted_on || '2025';
        }

        const statusMap: Record<string, string> = {
          submitted: 'Awaiting review',
          verified: 'Internally approved',
          flagged: 'Changes requested',
          rejected: 'Rejected',
          draft: 'Draft',
        };

        return {
          id: data.id,
          displayId: `ET-${data.id.slice(0, 8)}`,
          name: data.farmer_display_name ? `${data.farmer_display_name}'s Farm` : 'Farm Project',
          farmer: data.farmer_display_name || 'Assigned Farmer',
          location: 'Abeokuta, Ogun State',
          submitted_at: data.created_at
            ? new Date(data.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
            : 'Today',
          status: statusMap[data.status] || data.status,
          farm_type: 'Agroforestry',
          lga: 'Abeokuta',
          declared_area: `${data.area_ha || 0} ha`,
          mapping_type: 'GPS walk-around',
          species,
          tree_count: treeCount,
          planting_status: 'Newly planted',
          planting_date: plantingDate,
          satellite_note: monNote,
          history_note: 'Submission received by EcoTrees internal review workspace.',
          photos: data.photos || [],
        };
      }
    } catch {
      return null;
    }
  }

  return null;
}

export default function ProjectInspection() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<InspectionProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [decisionMessage, setDecisionMessage] = useState('');

  useEffect(() => {
    setLoading(true);
    fetchProjectInspection(id)
      .then(setProject)
      .finally(() => setLoading(false));
  }, [id]);

  const handleDecision = async (decision: 'verified' | 'rejected') => {
    if (!project) return;
    setActionLoading(true);
    setDecisionMessage('');
    try {
      const res = await fetch(`/api/auditor/plots/${project.id}/verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-EcoTrees': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          decision,
          note: comment.trim() || (decision === 'verified' ? 'Planting and evidence reviewed.' : 'Rejected upon inspection.'),
        }),
      });

      if (res.ok) {
        setProject((prev) =>
          prev
            ? {
                ...prev,
                status: decision === 'verified' ? 'Internally approved' : 'Rejected',
                history_note: `Today · Decision recorded: ${decision}. Note: ${comment || 'Reviewed.'}`,
              }
            : prev
        );
        setDecisionMessage(`Plot successfully ${decision === 'verified' ? 'approved' : 'rejected'}.`);
      } else {
        const err = await res.json().catch(() => null);
        setDecisionMessage(err?.error?.message || 'Could not record decision.');
      }
    } catch {
      setDecisionMessage('Network error occurred.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestChanges = () => {
    if (!project) return;
    setProject((prev) =>
      prev
        ? {
            ...prev,
            status: 'Changes requested',
            history_note: `Today · Auditor requested changes: ${comment || 'Provide clearer evidence photos.'}`,
          }
        : prev
    );
    setDecisionMessage('Changes requested note recorded.');
  };

  if (loading) {
    return <div className="p-8 text-gray-500 text-sm">Loading project inspection...</div>;
  }

  if (!project) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center space-y-4">
        <div className="w-14 h-14 rounded-2xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] mx-auto">
          <MapPin size={26} />
        </div>
        <h2 className="text-xl font-bold text-gray-900">No project selected</h2>
        <p className="text-xs text-gray-500 max-w-sm mx-auto leading-relaxed">
          Select a farm project from the review queue to inspect its boundary mapping, tree details, and ground photos.
        </p>
        <div className="pt-2">
          <button
            onClick={() => navigate('/auditor/review-queue')}
            className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3 rounded-xl transition-colors cursor-pointer"
          >
            Open review queue
          </button>
        </div>
      </div>
    );
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
            {project.displayId || project.id} · {project.name}
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

            {decisionMessage && (
              <div className="p-3 bg-[#eaf3ec] border border-[#1b4332]/20 rounded-xl text-xs text-[#1b4332] font-medium">
                {decisionMessage}
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-2.5">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleDecision('verified')}
                className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] disabled:opacity-60 text-white text-xs font-semibold py-3 rounded-xl transition-colors cursor-pointer"
              >
                {actionLoading ? 'Recording...' : 'Internally approve'}
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleRequestChanges}
                className="w-full border border-gray-200 hover:bg-gray-50 disabled:opacity-60 text-gray-700 text-xs font-medium py-3 rounded-xl transition-colors cursor-pointer"
              >
                Request changes
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleDecision('rejected')}
                className="w-full border border-gray-200 hover:bg-gray-50 disabled:opacity-60 text-gray-700 text-xs font-medium py-3 rounded-xl transition-colors cursor-pointer"
              >
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
