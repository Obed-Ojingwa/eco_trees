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

// Fetch function calling backend directly with clean empty state
async function fetchAuditorOverview(): Promise<OverviewData> {
  try {
    const res = await fetch('/api/plots', { credentials: 'include' });
    if (!res.ok) throw new Error('API unavailable');
    const json = await res.json();
    if (json && Array.isArray(json.items)) {
      const items = json.items as {
        id: string;
        farmer_display_name?: string;
        status?: string;
        flags?: string[];
      }[];

      const awaiting = items.filter((p) => p.status === 'submitted').length;
      const verified = items.filter((p) => p.status === 'verified').length;
      const flagged = items.filter((p) => p.status === 'flagged').length;
      const rejected = items.filter((p) => p.status === 'rejected').length;

      const priorityQueue: PriorityQueueItem[] = items.slice(0, 3).map((p) => ({
        id: `ET-${p.id.slice(0, 8)}`,
        farm: p.farmer_display_name ? `${p.farmer_display_name}'s Farm` : 'Farm Project',
        status:
          p.status === 'verified'
            ? 'Internally approved'
            : p.status === 'submitted'
            ? 'Awaiting review'
            : p.status === 'draft'
            ? 'Draft'
            : p.status || 'Awaiting review',
      }));

      return {
        stats: {
          awaiting_review: String(awaiting).padStart(2, '0'),
          under_review: String(items.filter((p) => p.status === 'submitted' || p.status === 'draft').length).padStart(2, '0'),
          resubmitted: String(flagged).padStart(2, '0'),
          internally_approved: String(verified).padStart(2, '0'),
          changes_requested: String(flagged).padStart(2, '0'),
          rejected: String(rejected).padStart(2, '0'),
        },
        priority_queue: priorityQueue,
        recent_activity: [],
      };
    }
    throw new Error('No items');
  } catch {
    // Empty state fallback
    return {
      stats: {
        awaiting_review: '00',
        under_review: '00',
        resubmitted: '00',
        internally_approved: '00',
        changes_requested: '00',
        rejected: '00',
      },
      priority_queue: [],
      recent_activity: [],
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
              {data.priority_queue.length > 0 ? (
                data.priority_queue.map((item) => (
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
                ))
              ) : (
                <div className="py-10 text-center text-xs text-gray-400 bg-[#f8faf8] rounded-2xl border border-dashed border-gray-200">
                  No projects waiting in priority queue.
                </div>
              )}
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
            {data.recent_activity.length > 0 ? (
              data.recent_activity.map((act, idx) => (
                <div key={idx} className="text-xs">
                  <p className="text-gray-700 font-medium leading-relaxed">
                    {act.actor} · <span className="text-gray-800 font-semibold">{act.target}</span>
                  </p>
                  <p className="text-gray-400 mt-0.5">· {act.time}</p>
                </div>
              ))
            ) : (
              <div className="py-10 text-center text-xs text-gray-400">
                No recent activity recorded.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
