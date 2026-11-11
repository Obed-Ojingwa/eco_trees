import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';

async function registerFarmerAccount(
  fullName: string,
  emailOrPhone: string,
  secret: string
): Promise<void> {
  let phone = emailOrPhone.replace(/\s+/g, '');
  if (phone.startsWith('0') && phone.length === 11) {
    phone = '+234' + phone.slice(1);
  } else if (!phone.startsWith('+')) {
    phone = '+' + phone;
  }

  // Ensure PIN is numeric
  const pin = secret.replace(/\D/g, '').padEnd(4, '0').slice(0, 8);

  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-EcoTrees': '1',
    },
    credentials: 'include',
    body: JSON.stringify({
      display_name: fullName,
      phone,
      pin,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    if (errorData?.error?.message) {
      throw new Error(errorData.error.message);
    }
    throw new Error('Registration failed. Please check your details.');
  }
}

export default function FarmerSignup() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [emailOrPhone, setEmailOrPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!fullName.trim() || !emailOrPhone.trim() || !password.trim()) {
      setErrorMessage('Please fill in all fields to create your account.');
      return;
    }

    setLoading(true);
    try {
      await registerFarmerAccount(fullName.trim(), emailOrPhone.trim(), password.trim());
      navigate('/farmer/overview');
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to create account. Please check your information.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Create your account
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Start with your email. You can complete your profile later.
        </p>
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left Form (8 cols) */}
        <div className="md:col-span-8 bg-white rounded-2xl border border-gray-100 p-8 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-5">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-100 flex items-center gap-2 text-xs text-red-700">
              <AlertCircle size={15} className="shrink-0 text-red-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Full name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
                className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none transition-colors"
              />
            </div>

            {/* Email / Phone */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                type="text"
                value={emailOrPhone}
                onChange={(e) => setEmailOrPhone(e.target.value)}
                placeholder="name@example.com"
                className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none transition-colors"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer disabled:opacity-60"
              >
                {loading ? 'Creating account...' : 'Create account'}
              </button>
            </div>
          </form>

          <p className="text-xs text-gray-500 pt-2">
            Already have an account?{' '}
            <Link to="/login" className="text-gray-900 font-medium hover:underline">
              Log in
            </Link>
          </p>
        </div>

        {/* Right Info Box (4 cols) */}
        <div className="md:col-span-4 bg-[#f2f7f4] rounded-2xl p-6">
          <h3 className="font-bold text-sm text-gray-900">
            Your account, your farms
          </h3>
          <p className="text-xs text-gray-600 mt-2 leading-relaxed">
            You can register more than one farm under this account.
          </p>
        </div>
      </div>
    </div>
  );
}
