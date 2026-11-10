import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  ListChecks,
  Folder,
  RotateCcw,
  Settings,
  HelpCircle,
  User,
} from 'lucide-react';

interface AuditorProfile {
  display_name: string;
  role: string;
}

async function fetchAuditorProfile(): Promise<AuditorProfile> {
  try {
    const res = await fetch('/api/me');
    if (!res.ok) throw new Error();
    const data = await res.json();
    return {
      display_name: data.display_name || 'Auditor',
      role: data.role === 'auditor' ? 'Auditor' : (data.role || 'Team member'),
    };
  } catch {
    return { display_name: 'Auditor', role: 'Team member' };
  }
}

export default function AuditorSidebar() {
  const [profile, setProfile] = useState<AuditorProfile>({
    display_name: 'Auditor',
    role: 'Team member',
  });

  useEffect(() => {
    fetchAuditorProfile().then(setProfile);
  }, []);

  const navItems = [
    { name: 'Overview', to: '/auditor/overview', icon: LayoutGrid },
    { name: 'Review queue', to: '/auditor/review-queue', icon: ListChecks },
    { name: 'Farm projects', to: '/auditor/farm-projects', icon: Folder },
    { name: 'Review history', to: '/auditor/review-history', icon: RotateCcw },
    { name: 'Settings', to: '/auditor/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-100 flex flex-col justify-between p-5 min-h-screen select-none shrink-0">
      <div>
        <p className="text-[11px] font-semibold tracking-wider text-gray-400 uppercase px-3 mb-4">
          Auditor Workspace
        </p>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-[#eaf3ec] text-[#1b4332]'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      className={isActive ? 'text-[#1b4332]' : 'text-gray-500'}
                    />
                    <span>{item.name}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="space-y-4 pt-4">
        {/* Help Card */}
        <div className="bg-[#f2f7f4] rounded-2xl p-4">
          <HelpCircle size={20} className="text-[#1b4332]" />
          <h4 className="font-semibold text-gray-900 text-sm mt-2">
            Need a hand?
          </h4>
          <p className="text-xs text-gray-500 mt-1 cursor-pointer hover:underline">
            Read the review standards
          </p>
        </div>

        {/* Auditor Profile */}
        <div className="flex items-center gap-3 px-1 py-1">
          <div className="w-8 h-8 rounded-full border border-gray-200 flex items-center justify-center text-gray-600 bg-white">
            <User size={16} />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900 leading-none">
              {profile.display_name}
            </p>
            <p className="text-xs text-gray-400 mt-1 leading-none">
              {profile.role}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
