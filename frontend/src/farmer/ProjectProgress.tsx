import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Clock, Circle, Info } from 'lucide-react';

interface FarmProgressData {
  farm_name: string;
  submitted_date: string;
  status: string;
}

export default function ProjectProgress() {
  const navigate = useNavigate();
  const [data, setData] = useState<FarmProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/plots', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (json && Array.isArray(json.items) && json.items.length > 0) {
          const plot = json.items[0];
          const statusMap: Record<string, string> = {
            draft: 'Draft',
            submitted: 'Under review',
            verified: 'Internally approved',
            flagged: 'Changes requested',
            rejected: 'Rejected',
          };
          setData({
            farm_name: plot.farmer_display_name ? `${plot.farmer_display_name}'s Farm` : 'Farm Project',
            submitted_date: new Date(plot.created_at || Date.now()).toLocaleDateString('en-GB', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            }),
            status: statusMap[plot.status] || 'Under review',
          });
        }
      })
      .catch(() => {
        // empty state
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-gray-500 text-sm">Loading project progress...</div>;
  }

  if (!data) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center space-y-4">
        <div className="w-14 h-14 rounded-2xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] mx-auto">
          <Clock size={26} />
        </div>
        <h2 className="text-xl font-bold text-gray-900">No project in review</h2>
        <p className="text-xs text-gray-500 max-w-sm mx-auto leading-relaxed">
          You haven&apos;t submitted a farm project for review yet. Register your farm to track verification progress here.
        </p>
        <div className="pt-2">
          <button
            onClick={() => navigate('/farmer/register')}
            className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3 rounded-xl transition-colors cursor-pointer"
          >
            Register a farm
          </button>
        </div>
      </div>
    );
  }

  const isApproved = data.status === 'Internally approved';
  const isChanges = data.status === 'Changes requested';

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Project progress
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          See where your farm project stands.
        </p>
      </div>

      {/* Farm Banner Card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-gray-900">
            {data.farm_name}
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Submitted · {data.submitted_date}
          </p>
        </div>

        <span className="bg-[#fef3c7] text-[#92400e] text-xs font-semibold px-3.5 py-1 rounded-full">
          {data.status}
        </span>
      </div>

      {/* Project Timeline Section */}
      <div className="space-y-4">
        <h3 className="font-semibold text-sm text-gray-900">
          Project timeline
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Step 1: Submission received */}
          <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2">
            <CheckCircle2 size={20} className="text-[#1b4332]" />
            <h4 className="font-bold text-sm text-gray-900 pt-1">
              Submission received
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed">
              Your farm details and photos are with our team.
            </p>
          </div>

          {/* Step 2: Under review */}
          <div className={`bg-[#f2f7f4] rounded-2xl p-6 space-y-2 ${isApproved ? 'opacity-80' : 'border border-[#1b4332]/20'}`}>
            <Clock size={20} className={isApproved ? 'text-gray-400' : 'text-[#1b4332]'} />
            <h4 className={`font-bold text-sm pt-1 ${isApproved ? 'text-gray-900' : 'text-[#1b4332]'}`}>
              Under review
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed font-medium">
              {isApproved ? 'Review completed.' : isChanges ? 'Changes requested by auditor.' : 'Our team is taking a closer look.'}
            </p>
          </div>

          {/* Step 3: Review decision */}
          <div className={`bg-[#f2f7f4] rounded-2xl p-6 space-y-2 ${isApproved ? 'border border-[#1b4332]/20' : 'opacity-80'}`}>
            {isApproved ? (
              <CheckCircle2 size={20} className="text-[#1b4332]" />
            ) : (
              <Circle size={20} className="text-gray-400" />
            )}
            <h4 className={`font-bold text-sm pt-1 ${isApproved ? 'text-[#1b4332]' : 'text-gray-900'}`}>
              Review decision
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isApproved
                ? 'Internally approved by EcoTrees review team.'
                : 'We’ll let you know here when there’s news.'}
            </p>
          </div>
        </div>
      </div>

      {/* Important Disclaimer Banner */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Important</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          Internal approval is not formal carbon-credit certification.
        </p>
      </div>
    </div>
  );
}
