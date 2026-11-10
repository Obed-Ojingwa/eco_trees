import { Outlet, NavLink, Link } from 'react-router-dom';

export default function BuyerLayout() {
  const navLinks = [
    { name: 'Explore projects', to: '/buyer/explore' },
    { name: 'How it works', to: '/buyer/how-it-works' },
    { name: 'My portfolio', to: '/buyer/portfolio' },
  ];

  return (
    <div className="min-h-screen bg-[#f7f9f8] flex flex-col font-sans text-gray-900">
      {/* Top Navigation Bar */}
      <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-8 sticky top-0 z-20">
        {/* Left: EcoTrees Logo */}
        <Link
          to="/buyer/explore"
          className="flex items-center gap-2.5 hover:opacity-90 transition-opacity cursor-pointer"
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

        {/* Center: Navigation Links */}
        <nav className="flex items-center gap-8 text-xs">
          {navLinks.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `transition-colors ${
                  isActive
                    ? 'text-[#1b4332] font-semibold'
                    : 'text-gray-600 hover:text-gray-900 font-medium'
                }`
              }
            >
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Right: Sign in Button */}
        <div>
          <Link
            to="/login"
            className="border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold px-4 py-2 rounded-lg transition-colors inline-block"
          >
            Sign in
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-gray-100/80 text-center text-xs text-gray-400">
        EcoTrees · Demo marketplace. Not certified carbon credits.
      </footer>
    </div>
  );
}
