import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';

interface AuthUser {
  id: string;
  role: string;
  display_name: string;
  phone?: string | null;
  email?: string | null;
  kyc_verified: boolean;
}

interface LoginResponse {
  user: AuthUser;
  expires_in_seconds: number;
}

async function performLogin(identifier: string, secret: string): Promise<LoginResponse> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-EcoTrees': '1',
    },
    credentials: 'include',
    body: JSON.stringify({ identifier, secret }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const message =
      errorData?.error?.message ||
      (res.status === 401
        ? 'Invalid phone/email or PIN/password.'
        : res.status === 423
        ? 'Account is temporarily locked. Try again later.'
        : 'Sign in failed. Please check your details.');
    throw new Error(message);
  }

  return await res.json();
}

export default function Login() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [secret, setSecret] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!identifier.trim() || !secret.trim()) {
      setErrorMessage('Please enter both identifier and PIN/password.');
      return;
    }

    setLoading(true);
    try {
      const response = await performLogin(identifier.trim(), secret.trim());
      // On success, redirect to auditor workspace or appropriate view
      if (response.user.role === 'auditor' || response.user.role === 'admin') {
        navigate('/auditor/overview');
      } else {
        navigate('/auditor/overview');
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred during sign in.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Demo shortcut for quick review testing
  const handleQuickAuditorDemo = () => {
    setIdentifier('auditor@ecotrees.org');
    setSecret('AuditorPass123!');
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
          <h1 className="text-xl font-bold text-gray-900">Welcome back</h1>
          <p className="text-xs text-gray-500 mt-1">
            Sign in to access your verification workspace
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-100 flex items-start gap-2.5 text-xs text-red-700">
            <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-600" />
            <div className="flex-1">
              <span>{errorMessage}</span>
              {errorMessage.includes('Failed to fetch') && (
                <p className="mt-1 text-[11px] text-red-600">
                  Backend offline? You can still browse via the link below.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Phone number or Email
            </label>
            <div className="relative">
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="+2348000000001 or name@ecotrees.org"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9"
              />
              <User
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
            </div>
            <p className="text-[11px] text-gray-400 mt-1">
              Farmers use phone; staff use provisioned email.
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-gray-700">
                PIN or Password
              </label>
            </div>
            <div className="relative">
              <input
                type={showSecret ? 'text' : 'password'}
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                placeholder="Enter PIN (digits) or password"
                className="w-full text-xs text-gray-900 px-3.5 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] focus:ring-1 focus:ring-[#1b4332] outline-none transition-all pl-9 pr-10"
              />
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                {showSecret ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3.5 rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-2 mt-2 disabled:opacity-60"
          >
            {loading ? (
              <span>Signing in...</span>
            ) : (
              <>
                <span>Sign in</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Helper */}
        <div className="mt-6 pt-5 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <button
            type="button"
            onClick={handleQuickAuditorDemo}
            className="text-[11px] text-gray-400 hover:text-[#1b4332] transition-colors cursor-pointer"
          >
            Fill auditor demo credentials
          </button>

          <Link
            to="/auditor/overview"
            className="text-[11px] text-gray-400 hover:text-[#1b4332] transition-colors"
          >
            Skip to Auditor Workspace &rarr;
          </Link>
        </div>

        {/* Switch to Signup */}
        <div className="mt-5 text-center text-xs text-gray-500">
          Are you a farmer?{' '}
          <Link
            to="/signup"
            className="text-[#1b4332] font-semibold hover:underline"
          >
            Register farm account
          </Link>
        </div>
      </div>
    </div>
  );
}
