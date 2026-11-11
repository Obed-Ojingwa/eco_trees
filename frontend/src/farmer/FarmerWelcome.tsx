import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle } from 'lucide-react';

export default function FarmerWelcome() {
  const navigate = useNavigate();
  const [role, setRole] = useState<'farmer' | 'auditor' | 'buyer'>('farmer');

  const handleGetStarted = () => {
    if (role === 'farmer') {
      navigate('/farmer/signup');
    } else if (role === 'auditor') {
      navigate('/auditor/overview');
    } else {
      navigate('/buyer/explore');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-[#1b4332]">
          Welcome to EcoTrees
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Your farm, your trees, your story. Let’s get them on record.
        </p>
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left Green Banner (6 cols) */}
        <div className="md:col-span-6 bg-[#eaf3ec] rounded-2xl p-8 flex flex-col justify-between min-h-[340px]">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 leading-snug">
              Grow trees. Build a greener future.
            </h2>
            <p className="text-xs text-gray-600 mt-3 leading-relaxed">
              Add a few details and photos. We’ll guide you through the rest.
            </p>
          </div>

          <div className="mt-8">
            <svg
              className="w-16 h-16 text-[#1b4332]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M7 20h10" />
              <path d="M12 20v-8" />
              <path d="M12 12a5 5 0 0 1-5-5c0-3 2.5-6 5-7 2.5 1 5 4 5 7a5 5 0 0 1-5 5z" />
            </svg>
          </div>
        </div>

        {/* Right Role Selection Form (6 cols) */}
        <div className="md:col-span-6 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">
            How do you want to sign up?
          </h3>

          <div className="space-y-3">
            {/* Option: Farmer */}
            <div
              onClick={() => setRole('farmer')}
              className={`p-5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                role === 'farmer'
                  ? 'border-[#1b4332]/40 bg-white shadow-sm ring-1 ring-[#1b4332]/30'
                  : 'border-gray-200/80 bg-white hover:border-gray-300'
              }`}
            >
              <span className="font-semibold text-sm text-gray-900">Farmer</span>
              {role === 'farmer' ? (
                <CheckCircle2 size={20} className="text-[#1b4332]" />
              ) : (
                <Circle size={20} className="text-gray-300" />
              )}
            </div>

            {/* Option: Auditor */}
            <div
              onClick={() => setRole('auditor')}
              className={`p-5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                role === 'auditor'
                  ? 'border-[#1b4332]/40 bg-white shadow-sm ring-1 ring-[#1b4332]/30'
                  : 'border-gray-200/80 bg-white hover:border-gray-300'
              }`}
            >
              <span className="font-semibold text-sm text-gray-900">Auditor</span>
              {role === 'auditor' ? (
                <CheckCircle2 size={20} className="text-[#1b4332]" />
              ) : (
                <Circle size={20} className="text-gray-300" />
              )}
            </div>

            {/* Option: Buyer */}
            <div
              onClick={() => setRole('buyer')}
              className={`p-5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                role === 'buyer'
                  ? 'border-[#1b4332]/40 bg-white shadow-sm ring-1 ring-[#1b4332]/30'
                  : 'border-gray-200/80 bg-white hover:border-gray-300'
              }`}
            >
              <span className="font-semibold text-sm text-gray-900">Buyer</span>
              {role === 'buyer' ? (
                <CheckCircle2 size={20} className="text-[#1b4332]" />
              ) : (
                <Circle size={20} className="text-gray-300" />
              )}
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleGetStarted}
              className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer"
            >
              Get started
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
