import { useState } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Globe, Bell, User } from 'lucide-react';
import AuditorSidebar from './AuditorSidebar';

export default function AuditorLayout() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  // Determine current section for breadcrumbs
  const getSectionTitle = () => {
    const path = location.pathname;
    if (path.includes('project-inspection')) return 'Project inspection';
    if (path.includes('review-queue')) return 'Review queue';
    if (path.includes('farm-projects')) return 'Farm projects';
    if (path.includes('review-history')) return 'Review history';
    if (path.includes('settings')) return 'Settings';
    return 'Overview';
  };

  return (
    <div className="h-screen bg-[#f7f9f8] flex flex-col font-sans text-gray-900 overflow-hidden">
      {/* Top Header */}
      <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 shrink-0 z-20">
        <div className="flex items-center gap-12">
          {/* Logo */}
          <Link
            to="/auditor/overview"
            className="flex items-center gap-2.5 w-52 shrink-0 hover:opacity-90 transition-opacity cursor-pointer"
          >
            <svg
              className="w-6 h-6 text-[#1b4332]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22v-7" />
              <path d="M12 15a5 5 0 0 1-5-5c0-3 2.5-6 5-8 2.5 2 5 5 5 8a5 5 0 0 1-5 5z" />
              <path d="M7 10a4 4 0 0 0-4 4c0 2 1.5 3.5 3.5 3.5" />
              <path d="M17 10a4 4 0 0 1 4 4c0 2-1.5 3.5-3.5 3.5" />
            </svg>
            <span className="font-bold text-lg tracking-tight text-[#1b4332]">
              EcoTrees
            </span>
          </Link>

          {/* Breadcrumbs */}
          <div className="text-xs text-gray-500 font-normal">
            <Link to="/auditor/overview" className="hover:text-gray-800 transition-colors">
              EcoTrees
            </Link>
            <span className="mx-1 text-gray-300">/</span> {getSectionTitle()}
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-6">
          <button className="flex items-center gap-2 text-xs font-medium text-gray-600 hover:text-gray-900 cursor-pointer">
            <Globe size={15} className="text-gray-500" />
            <span>EN · Pidgin</span>
          </button>

          <button className="text-gray-500 hover:text-gray-900 cursor-pointer">
            <Bell size={18} />
          </button>

          <Link
            to="/login"
            title="Account / Sign in"
            className="w-7 h-7 rounded-full border border-gray-200 flex items-center justify-center text-gray-600 hover:text-gray-900 bg-white transition-colors"
          >
            <User size={15} />
          </Link>
        </div>
      </header>

      {/* Body: Sidebar + Main Content Frame */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <AuditorSidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
        />

        {/* Scrollable Children Container */}
        <main className="flex-1 overflow-y-auto p-8 min-w-0 flex flex-col justify-between">
          <div className="flex-1">
            <Outlet />
          </div>

          {/* Footer */}
          <footer className="mt-12 pt-6 pb-2 border-t border-gray-100/60 flex items-center justify-between text-xs text-gray-400 shrink-0">
            <span>EcoTrees · Internal review workspace</span>
            <a
              href="#help"
              className="hover:text-gray-600 transition-colors"
            >
              Help &amp; support
            </a>
          </footer>
        </main>
      </div>
    </div>
  );
}
