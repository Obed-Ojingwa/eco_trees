import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Phone, Lock, Eye, EyeOff, AlertCircle, ArrowRight } from 'lucide-react';

interface AuthUser {
  id: string;
  role: string;
  display_name: string;
  phone?: string | null;
  email?: string | null;
  kyc_verified: boolean;
}

interface RegisterResponse {
  user: AuthUser;
  expires_in_seconds: number;
}

async function performRegistration(
  displayName: string,
  phone: string,
  pin: string
): Promise<RegisterResponse> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-EcoTrees': '1',
    },
    credentials: 'include',
    body: JSON.stringify({
      display_name: displayName,
      phone,
      pin,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const message =
      errorData?.error?.message ||
      (res.status === 409
        ? 'This phone number is already registered.'
        : res.status === 422
        ? 'Please check your inputs (valid phone digits & 4-8 digit numeric PIN).'
        : 'Registration failed. Please try again.');
    throw new Error(message);
  }

  return await res.json();
}

export default function Signup() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState('');
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!displayName.trim()) {
      setErrorMessage('Please enter your full name or farm display name.');
      return;
    }

    const cleanPhone = phone.trim();
    if (!cleanPhone || cleanPhone.length < 7) {
      setErrorMessage('Please enter a valid phone number (at least 7 digits).');
      return;
    }

    if (!/^\d{4,8}$/.test(pin)) {
      setErrorMessage('PIN must be 4 to 8 digits (numeric only).');
      return;
    }

    if (pin !== confirmPin) {
      setErrorMessage('PIN confirmation does not match.');
      return;
    }

    setLoading(true);
    try {
      await performRegistration(displayName.trim(), cleanPhone, pin);
      // On successful registration as farmer, navigate to overview or dashboard
      navigate('/auditor/overview');
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred during registration.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f7f9f8] flex flex-col justify-center items-center p-4">
      {/* Container */}
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-100 p-8 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
        {/* Brand Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2.5 mb-2">
            <svg
              className="w-7 h-7 text-[#1b4332]"
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
            <span className="font-bold text-2xl tracking-tight text-[#1b4332]">
              EcoTrees
            </span>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Create Farm Account</h1>
          <p className="text-xs text-gray-500 mt-1">
            Register your farm to record plots and verify trees
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-100 flex items-start gap-2.5 text-xs text-red-700">
            <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-600" />
            <div className="flex-1">
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Display Name */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Full name / Farm display name
            </label>
            <div className="relative">
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Babatunde Musa"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9"
              />
              <User
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
            </div>
          </div>

          {/* Phone */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Phone number
            </label>
            <div className="relative">
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+2348012345678"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9"
              />
              <Phone
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
            </div>
            <p className="text-[11px] text-gray-400 mt-1">
              Used for your sign-in identifier (7 to 19 digits).
            </p>
          </div>

          {/* PIN */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Security PIN (4 to 8 digits)
            </label>
            <div className="relative">
              <input
                type={showPin ? 'text' : 'password'}
                maxLength={8}
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
                placeholder="e.g. 2468"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9 pr-10"
              />
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <button
                type="button"
                onClick={() => setShowPin(!showPin)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                {showPin ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Confirm PIN */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Confirm Security PIN
            </label>
            <div className="relative">
              <input
                type={showPin ? 'text' : 'password'}
                maxLength={8}
                value={confirmPin}
                onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ''))}
                placeholder="Repeat your PIN"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9"
              />
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3.5 rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-2 mt-4 disabled:opacity-60"
          >
            {loading ? (
              <span>Creating account...</span>
            ) : (
              <>
                <span>Register account</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </form>

        {/* Notice for provisioned staff */}
        <div className="mt-6 p-3 rounded-xl bg-gray-50 border border-gray-100 text-[11px] text-gray-500 leading-relaxed">
          <strong className="text-gray-700">Auditor or Admin?</strong> Provisioned staff roles cannot self-register; they are created by your team administrator.
        </div>

        {/* Switch to Login */}
        <div className="mt-5 text-center text-xs text-gray-500">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-[#1b4332] font-semibold hover:underline"
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
