import { useEffect, useState } from 'react';

interface AuditorSettingsData {
  account_summary: string;
  notifications_summary: string;
  standards_summary: string;
}

async function fetchAuditorSettings(): Promise<AuditorSettingsData> {
  try {
    const res = await fetch('/api/me', { credentials: 'include' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    return {
      account_summary: `${data.display_name || 'Auditor'} · ${data.email || data.phone || 'auditor@ecotrees.org'} · ${data.role || 'Auditor'}`,
      notifications_summary:
        'New submissions · Resubmissions · Assignment updates · Decision confirmations',
      standards_summary:
        'Base each decision on the information available. Explain what needs to change, and remember: internal approval is not certification.',
    };
  } catch {
    // Exact fallback matching the UI specification
    return {
      account_summary: 'Name · Email · Assigned role · Team',
      notifications_summary:
        'New submissions · Resubmissions · Assignment updates · Decision confirmations',
      standards_summary:
        'Base each decision on the information available. Explain what needs to change, and remember: internal approval is not certification.',
    };
  }
}

export default function AuditorSettings() {
  const [settings, setSettings] = useState<AuditorSettingsData | null>(null);

  useEffect(() => {
    fetchAuditorSettings().then(setSettings);
  }, []);

  if (!settings) return null;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Settings
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Update your reviewer details and notification preferences.
        </p>
      </div>

      {/* 3 Horizontal Cards matching design */}
      <div className="space-y-4">
        {/* Card 1: Reviewer account */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <h3 className="text-sm font-semibold text-gray-900">
            Reviewer account
          </h3>
          <p className="text-xs text-gray-600 mt-3">
            {settings.account_summary}
          </p>
        </div>

        {/* Card 2: In-app notifications */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <h3 className="text-sm font-semibold text-gray-900">
            In-app notifications
          </h3>
          <p className="text-xs text-gray-600 mt-3">
            {settings.notifications_summary}
          </p>
        </div>

        {/* Card 3: Review standards */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <h3 className="text-sm font-semibold text-gray-900">
            Review standards
          </h3>
          <p className="text-xs text-gray-600 mt-3 leading-relaxed">
            {settings.standards_summary}
          </p>
        </div>
      </div>
    </div>
  );
}
