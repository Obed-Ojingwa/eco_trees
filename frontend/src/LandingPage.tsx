import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Trees,
  ShieldCheck,
  ShoppingBag,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Globe,
  Sparkles,
} from 'lucide-react';

interface CurrentUser {
  display_name: string;
  role: string;
}

type SessionState =
  | { status: 'checking' }
  | { status: 'signed-out' }
  | { status: 'signed-in'; user: CurrentUser }
  | { status: 'unavailable' };

export default function LandingPage() {
  const navigate = useNavigate();
  const [session, setSession] = useState<SessionState>({ status: 'checking' });

  useEffect(() => {
    const controller = new AbortController();

    fetch('/api/me', { credentials: 'include', signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) {
          setSession({ status: 'signed-out' });
          return;
        }
        if (!response.ok) {
          setSession({ status: 'unavailable' });
          return;
        }

        const user: CurrentUser = await response.json();
        setSession({ status: 'signed-in', user });
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setSession({ status: 'unavailable' });
        }
      });

    return () => controller.abort();
  }, []);

  const workspacePath =
    session.status === 'signed-in' && (session.user.role === 'auditor' || session.user.role === 'admin')
      ? '/auditor/overview'
      : session.status === 'signed-in' && session.user.role === 'buyer'
        ? '/buyer/explore'
        : '/farmer/overview';

  return (
    <div className="min-h-screen bg-[#f7f9f8] text-gray-900 flex flex-col font-sans selection:bg-[#1b4332] selection:text-white">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#1b4332] flex items-center justify-center text-white shadow-xs">
              <Trees size={20} />
            </div>
            <span className="font-bold text-xl tracking-tight text-[#1b4332]">
              EcoTrees
            </span>
          </Link>

          {/* Navigation links */}
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold text-gray-600">
            <Link to="/buyer/explore" className="hover:text-[#1b4332] transition-colors">
              Marketplace
            </Link>
            <Link to="/buyer/how-it-works" className="hover:text-[#1b4332] transition-colors">
              How it works
            </Link>
            <Link to="/farmer/overview" className="hover:text-[#1b4332] transition-colors">
              Farmer Workspace
            </Link>
            <Link to="/auditor/overview" className="hover:text-[#1b4332] transition-colors">
              Auditor Portal
            </Link>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500 mr-2">
              <Globe size={14} className="text-[#1b4332]" />
              <span className="font-medium text-gray-700">EN</span>
              <span className="text-gray-300">·</span>
              <span className="text-gray-400">Pidgin</span>
            </div>

            {session.status === 'signed-in' ? (
              <Link
                to={workspacePath}
                className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
              >
                <span className="max-w-32 truncate">{session.user.display_name}</span>
                <ArrowRight size={14} />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-xs font-semibold text-gray-700 hover:text-[#1b4332] px-3.5 py-2 rounded-xl transition-colors"
                >
                  Sign in
                </Link>

                {session.status === 'signed-out' && (
                  <Link
                    to="/login"
                    className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
                  >
                    <span>Get started</span>
                    <ArrowRight size={14} />
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden">
        {/* Subtle background gradient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-[#eaf3ec] to-transparent pointer-events-none -z-10 rounded-b-3xl opacity-60" />

        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-[#eaf3ec] text-[#1b4332] px-4 py-1.5 rounded-full text-xs font-semibold border border-[#1b4332]/10 shadow-2xs">
            <Sparkles size={14} className="text-[#1b4332]" />
            <span>Transparent Nature-Based Restoration in Nigeria</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-gray-900 leading-[1.12]">
            Empowering Farmers.{' '}
            <span className="text-[#1b4332] block sm:inline">
              Verifying Trees.
            </span>{' '}
            Restoring Landscapes.
          </h1>

          {/* Subheading */}
          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
            EcoTrees bridges smallholder agroforestry farmers with independent auditor verification and Sentinel-2 satellite monitoring—bringing real climate action and transparent proceeds to local communities.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-4">
            <button
              type="button"
              onClick={() => navigate('/farmer/welcome')}
              className="w-full sm:w-auto bg-[#1e4d3a] hover:bg-[#163c2c] text-white font-semibold text-xs sm:text-sm px-7 py-3.5 rounded-xl shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Register as a Farmer</span>
              <ArrowRight size={16} />
            </button>

            <button
              type="button"
              onClick={() => navigate('/buyer/explore')}
              className="w-full sm:w-auto bg-white hover:bg-gray-50 text-gray-800 font-semibold text-xs sm:text-sm px-7 py-3.5 rounded-xl border border-gray-200 shadow-2xs transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Explore Marketplace</span>
              <ShoppingBag size={16} className="text-gray-500" />
            </button>

            <button
              type="button"
              onClick={() => navigate('/auditor/overview')}
              className="w-full sm:w-auto bg-white hover:bg-gray-50 text-gray-800 font-semibold text-xs sm:text-sm px-6 py-3.5 rounded-xl border border-gray-200 shadow-2xs transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Auditor Portal</span>
              <ShieldCheck size={16} className="text-gray-500" />
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="pt-10 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
            <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-2xs">
              <div className="text-2xl font-bold text-[#1b4332]">100%</div>
              <p className="text-[11px] text-gray-500 mt-1">Geotagged GPS &amp; polygon boundary mapping</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-2xs">
              <div className="text-2xl font-bold text-[#1b4332]">Sentinel-2</div>
              <p className="text-[11px] text-gray-500 mt-1">Satellite NDVI vegetation monitoring</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-2xs">
              <div className="text-2xl font-bold text-[#1b4332]">4 Species</div>
              <p className="text-[11px] text-gray-500 mt-1">Gmelina, Cashew, Neem &amp; Mangrove</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-2xs">
              <div className="text-2xl font-bold text-[#1b4332]">Farmer-First</div>
              <p className="text-[11px] text-gray-500 mt-1">Transparent proceeds &amp; reward XP allocation</p>
            </div>
          </div>
        </div>
      </section>

      {/* Role Selector Section ("Who are you?") */}
      <section className="py-16 bg-white border-y border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
              Built for every step of restoration
            </h2>
            <p className="text-xs sm:text-sm text-gray-500">
              Select your role to access tailored workspaces, workflows, and tools.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Role 1: Farmer */}
            <div className="bg-[#f2f7f4] rounded-2xl p-7 flex flex-col justify-between hover:border-[#1b4332]/30 border border-transparent transition-all space-y-6">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-[#1b4332] shadow-2xs">
                  <Trees size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">
                    For Farmers
                  </h3>
                  <p className="text-xs text-gray-600 mt-2 leading-relaxed">
                    Map your farm with interactive boundary tools, record tree inventory, upload GPS-tagged photos, and track potential restoration income.
                  </p>
                </div>
                <ul className="space-y-2 text-xs text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Free interactive polygon map</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Tree planting XP points &amp; levels</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Direct bank account linking</span>
                  </li>
                </ul>
              </div>

              <button
                type="button"
                onClick={() => navigate('/farmer/overview')}
                className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Enter Farmer Workspace</span>
                <ChevronRight size={14} />
              </button>
            </div>

            {/* Role 2: Auditor */}
            <div className="bg-white rounded-2xl p-7 border border-gray-200/80 shadow-xs flex flex-col justify-between hover:border-[#1b4332]/40 transition-all space-y-6">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332]">
                  <ShieldCheck size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">
                    For Independent Auditors
                  </h3>
                  <p className="text-xs text-gray-600 mt-2 leading-relaxed">
                    Inspect priority review queues, audit boundary overlays, inspect ground evidence photos, and verify survival milestones before certification.
                  </p>
                </div>
                <ul className="space-y-2 text-xs text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Structured review queue</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Sentinel-2 NDVI observations</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#1b4332] shrink-0" />
                    <span>Auditor verification decision log</span>
                  </li>
                </ul>
              </div>

              <button
                type="button"
                onClick={() => navigate('/auditor/overview')}
                className="w-full bg-gray-900 hover:bg-black text-white text-xs font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Open Auditor Portal</span>
                <ChevronRight size={14} />
              </button>
            </div>

            {/* Role 3: Buyer */}
            <div className="bg-[#fbf4e2] rounded-2xl p-7 border border-[#f5e6c4] flex flex-col justify-between hover:border-amber-400 transition-all space-y-6">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-[#875d15] shadow-2xs">
                  <ShoppingBag size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-[#543d11]">
                    For Buyers &amp; Funders
                  </h3>
                  <p className="text-xs text-[#71541b] mt-2 leading-relaxed">
                    Explore verified nature-based projects, view transparent species and hectare metrics, checkout demo restoration units, and track portfolio certificates.
                  </p>
                </div>
                <ul className="space-y-2 text-xs text-[#71541b]">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#875d15] shrink-0" />
                    <span>Itemized restoration units</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#875d15] shrink-0" />
                    <span>Simulated mock bank checkout</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-[#875d15] shrink-0" />
                    <span>Digital portfolio tracking</span>
                  </li>
                </ul>
              </div>

              <button
                type="button"
                onClick={() => navigate('/buyer/explore')}
                className="w-full bg-[#875d15] hover:bg-[#6e4a0d] text-white text-xs font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Browse Marketplace</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 3-Step Process Walkthrough */}
      <section className="py-20 bg-[#f7f9f8]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center max-w-xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
              How the platform works
            </h2>
            <p className="text-xs sm:text-sm text-gray-500">
              From seeds in the ground to verified restoration units on the market.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Step 1 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-xs space-y-4">
              <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] font-bold text-sm">
                01
              </div>
              <h3 className="font-bold text-base text-gray-900">
                Plot Mapping &amp; Planting
              </h3>
              <p className="text-xs text-gray-600 leading-relaxed">
                Farmers trace their farm corners on our interactive map (or simulate GPS walk-around) and log planted species like Gmelina, Cashew, or Neem with real-time area calculation.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-xs space-y-4">
              <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] font-bold text-sm">
                02
              </div>
              <h3 className="font-bold text-base text-gray-900">
                Evidence &amp; Satellite MRV
              </h3>
              <p className="text-xs text-gray-600 leading-relaxed">
                Plot photos are tagged with GPS metadata and validated. Sentinel-2 satellite imagery continuously monitors vegetation health (NDVI) against local control buffers.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-xs space-y-4">
              <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] font-bold text-sm">
                03
              </div>
              <h3 className="font-bold text-base text-gray-900">
                Audited Listings &amp; Payouts
              </h3>
              <p className="text-xs text-gray-600 leading-relaxed">
                Once verified by auditors, plots form batches for the restoration marketplace. Supporters purchase demo units and transparent proceeds are allocated to farmers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to action footer banner */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 w-full">
        <div className="bg-[#1b4332] rounded-3xl p-8 sm:p-12 text-white flex flex-col md:flex-row items-center justify-between gap-8 shadow-sm">
          <div className="space-y-2 text-center md:text-left">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Ready to explore EcoTrees?
            </h2>
            <p className="text-xs sm:text-sm text-gray-300 max-w-md leading-relaxed">
              Sign in with seeded demo credentials or register a new farm account in minutes.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            <Link
              to="/login"
              className="bg-white hover:bg-gray-100 text-[#1b4332] text-xs font-bold px-6 py-3.5 rounded-xl text-center shadow-xs transition-colors"
            >
              Sign in to Workspace
            </Link>
            <Link
              to="/farmer/welcome"
              className="bg-[#2d6a4f] hover:bg-[#255740] text-white text-xs font-bold px-6 py-3.5 rounded-xl text-center transition-colors border border-white/20"
            >
              Create Farm Account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-10 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-[#1b4332] flex items-center justify-center text-white">
              <Trees size={14} />
            </div>
            <span className="font-semibold text-gray-900">EcoTrees</span>
            <span className="text-gray-400">· Farmer-first climate action</span>
          </div>

          <p className="text-[11px] text-gray-400 text-center sm:text-right">
            EcoTrees demo prototype. Internal verification records, not certified carbon credits.
          </p>
        </div>
      </footer>
    </div>
  );
}
