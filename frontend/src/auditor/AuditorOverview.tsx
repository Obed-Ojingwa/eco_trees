import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface OverviewStats {
  awaiting_review: string;
  under_review: string;
  resubmitted: string;
  internally_approved: string;
  changes_requested: string;
  rejected: string;
}

interface PriorityQueueItem {
  id: string;
  farm: string;
  status: string;
}

interface ActivityItem {
  actor: string;
  target: string;
  time: string;
}

interface OverviewData {
  stats: OverviewStats;
  priority_queue: PriorityQueueItem[];
  recent_activity: ActivityItem[];
}

// Fetch function calling backend directly with fallback
async function fetchAuditorOverview(): Promise<OverviewData> {
  try {
    const res = await fetch('/api/auditor/overview');
    if (!res.ok) throw new Error('API unavailable');
    return await res.json();
  } catch {
    // Minimal fallback matching the UI specification
    return {
      stats: {
        awaiting_review: '24',
        under_review: '08',
        resubmitted: '05',
        internally_approved: '36',
        changes_requested: '12',
        rejected: '03',
      },
      priority_queue: [
        { id: 'ET-00124', farm: 'Green Valley Farm', status: 'Resubmitted' },
        { id: 'ET-00118', farm: 'Sunrise Agro Farm', status: 'Awaiting review' },
        { id: 'ET-00109', farm: 'Olu Farm Project', status: 'Awaiting review' },
      ],
      recent_activity: [
        { actor: 'A. Bello requested changes', target: 'ET-00120', time: '10:42' },
        { actor: 'M. Ade internally approved', target: 'ET-00117', time: '09:15' },
        { actor: 'A. Bello reviewed evidence', target: 'ET-00115', time: 'Yesterday' },
      ],
    };
  }
}

export default function AuditorOverview() {
  const navigate = useNavigate();
  const [data, setData] = useState<OverviewData | null>(null);

  useEffect(() => {
    fetchAuditorOverview().then(setData);
  }, []);

  if (!data) {
    return <div className="p-8 text-gray-500 text-sm">Loading workspace...</div>;
  }

  const statCards = [
    { value: data.stats.awaiting_review, label: 'Awaiting review' },
    { value: data.stats.under_review, label: 'Currently under review' },
    { value: data.stats.resubmitted, label: 'Resubmitted projects' },
    {
      value: data.stats.internally_approved,
      label: 'Internally approved',
      highlightColor: 'text-[#1b4332]',
    },
    { value: data.stats.changes_requested, label: 'Changes requested' },
    { value: data.stats.rejected, label: 'Rejected projects' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Overview
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          See what needs attention and keep each review on track.
        </p>
      </div>

      {/* 6 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {statCards.map((card, idx) => (
          <div
            key={idx}
            className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
          >
            <div className="text-3xl font-bold text-gray-900 tracking-tight">
              {card.value}
            </div>
            <div
              className={`text-sm mt-3 ${
                card.highlightColor ? card.highlightColor : 'text-gray-600'
              }`}
            >
              {card.label}
            </div>
          </div>
        ))}
      </div>

      {/* Lower Section: Priority queue + Recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-1">
        {/* Priority review queue (Left, 8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-gray-100 p-6 flex flex-col justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              Priority review queue
            </h3>
            <p className="text-xs text-gray-500 mt-1 mb-5">
              Resubmissions first · then oldest pending submissions
            </p>

            <div className="space-y-3">
              {data.priority_queue.map((item) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/auditor/project-inspection/${item.id}`)}
                  className="bg-[#f8faf8] border border-gray-100/90 rounded-2xl px-5 py-4 text-sm text-gray-800 flex items-center cursor-pointer hover:bg-gray-100/70 transition-colors"
                >
                  <span className="font-semibold text-gray-900 mr-2">
                    {item.id}
                  </span>
                  <span className="text-gray-700">{item.farm}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span className="text-gray-600">{item.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-6">
            <button
              onClick={() => navigate('/auditor/review-queue')}
              className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-5 py-3 rounded-lg transition-colors cursor-pointer"
            >
              Open full review queue
            </button>
          </div>
        </div>

        {/* Recent activity (Right, 4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <h3 className="text-base font-semibold text-gray-900 mb-5">
            Recent activity
          </h3>

          <div className="space-y-5">
            {data.recent_activity.map((act, idx) => (
              <div key={idx} className="text-xs">
                <p className="text-gray-700 font-medium leading-relaxed">
                  {act.actor} · <span className="text-gray-800 font-semibold">{act.target}</span>
                </p>
                <p className="text-gray-400 mt-0.5">· {act.time}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
