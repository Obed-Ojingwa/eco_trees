import { useEffect, useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutGrid,
  MapPin,
  Clock,
  Wallet,
  User,
  HelpCircle,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface FarmerProfile {
  display_name: string;
  role: string;
  email?: string;
}

interface FarmerSidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

async function fetchFarmerProfile(): Promise<FarmerProfile> {
  try {
    const res = await fetch('/api/me');
    if (!res.ok) throw new Error();
    const data = await res.json();
    return {
      display_name: data.display_name || 'Ama Farmer',
      role: 'Farmer account',
      email: data.email || 'ama@example.com',
    };
  } catch {
    return {
      display_name: 'Ama Farmer',
      role: 'Farmer account',
      email: 'ama@example.com',
    };
  }
}

export default function FarmerSidebar({ collapsed = false, onToggle }: FarmerSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [profile, setProfile] = useState<FarmerProfile>({
    display_name: 'Ama Farmer',
    role: 'Farmer account',
  });

  useEffect(() => {
    fetchFarmerProfile().then(setProfile);
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'X-EcoTrees': '1' },
        credentials: 'include',
      });
    } finally {
      navigate('/login');
    }
  };

  const isGetStartedMode = location.pathname.includes('welcome') || location.pathname.includes('signup');

  const navItems = [
    { name: 'Overview', to: '/farmer/overview', icon: LayoutGrid },
    { name: 'My farms', to: '/farmer/farms', icon: MapPin },
    { name: 'Project progress', to: '/farmer/progress', icon: Clock },
    { name: 'Earnings', to: '/farmer/earnings', icon: Wallet },
    { name: 'My profile', to: '/farmer/profile', icon: User },
  ];

  return (
    <aside
      className={`bg-white border-r border-gray-100 flex flex-col justify-between transition-all duration-300 ease-in-out select-none shrink-0 h-full overflow-hidden ${
        collapsed ? 'w-20 p-3' : 'w-64 p-5'
      }`}
    >
      {/* Top Navigation */}
      <div className="flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-4 px-1 h-6">
          {!collapsed && (
            <p className="text-[11px] font-semibold tracking-wider text-gray-400 uppercase truncate">
              {isGetStartedMode ? 'Get Started' : 'Farmer Workspace'}
            </p>
          )}

          <button
            onClick={onToggle}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={`text-gray-400 hover:text-gray-800 hover:bg-gray-100 p-1 rounded-lg transition-colors cursor-pointer ${
              collapsed ? 'mx-auto' : ''
            }`}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={collapsed ? item.name : undefined}
                className={({ isActive }) =>
                  `flex items-center rounded-xl text-sm font-medium transition-colors ${
                    collapsed
                      ? 'justify-center py-2.5 px-0'
                      : 'gap-3 px-3 py-2.5'
                  } ${
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
                      className={`shrink-0 ${
                        isActive ? 'text-[#1b4332]' : 'text-gray-500'
                      }`}
                    />
                    {!collapsed && <span className="truncate">{item.name}</span>}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Section */}
      <div className="space-y-3 pt-3 border-t border-gray-50 shrink-0">
        {/* Help Card */}
        {collapsed ? (
          <div
            title="Need a hand? Talk to your field agent"
            className="bg-[#f2f7f4] rounded-xl p-2.5 flex items-center justify-center cursor-pointer hover:bg-[#e6f0e9] transition-colors"
          >
            <HelpCircle size={20} className="text-[#1b4332]" />
          </div>
        ) : (
          <div className="bg-[#f2f7f4] rounded-2xl p-4">
            <HelpCircle size={20} className="text-[#1b4332]" />
            <h4 className="font-semibold text-gray-900 text-sm mt-2">
              Need a hand?
            </h4>
            <p className="text-xs text-gray-500 mt-1 cursor-pointer hover:underline">
              Talk to your field agent
            </p>
          </div>
        )}

        {/* Farmer Profile */}
        {collapsed ? (
          <div className="flex flex-col items-center gap-2 pt-1">
            <div
              title={`${profile.display_name} (${profile.role})`}
              className="w-8 h-8 rounded-full border border-gray-200 flex items-center justify-center text-gray-600 bg-white"
            >
              <User size={16} />
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="text-gray-400 hover:text-red-600 transition-colors cursor-pointer p-1 rounded-lg"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between px-1 py-1">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-full border border-gray-200 flex items-center justify-center text-gray-600 bg-white shrink-0">
                <User size={16} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900 leading-none truncate">
                  {isGetStartedMode ? 'Your farmer journey' : profile.display_name}
                </p>
                <p className="text-xs text-gray-400 mt-1 leading-none truncate">
                  {isGetStartedMode ? 'Let’s grow together' : profile.role}
                </p>
              </div>
            </div>

            <button
              onClick={handleLogout}
              title="Sign out"
              className="text-gray-400 hover:text-red-600 transition-colors cursor-pointer p-1 rounded-lg shrink-0"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
