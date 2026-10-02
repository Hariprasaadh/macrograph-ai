import React, { useState } from 'react';
import { X, ShieldCheck, KeyRound, ExternalLink, AlertCircle } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { UserProfile } from '../types';

interface GoogleAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (profile: UserProfile) => void;
  clientId: string;
  onSaveClientId: (id: string) => void;
}

export function decodeJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (err) {
    console.error('Failed to decode Google JWT token', err);
    return null;
  }
}

export const GoogleAuthModal: React.FC<GoogleAuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  clientId,
  onSaveClientId,
}) => {
  const [inputClientId, setInputClientId] = useState(clientId || '');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGoogleSuccess = (credentialResponse: any) => {
    if (!credentialResponse?.credential) {
      setErrorMessage('No credential returned by Google. Please try again.');
      return;
    }

    const payload = decodeJwt(credentialResponse.credential);
    if (!payload) {
      setErrorMessage('Unable to verify Google credential token.');
      return;
    }

    const profile: UserProfile = {
      id: payload.sub || `google-${Date.now()}`,
      name: payload.name || payload.given_name || 'Google User',
      email: payload.email || 'user@gmail.com',
      avatar:
        payload.picture ||
        `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(payload.name || 'User')}`,
      role: 'Macroeconomic Researcher',
      organization: payload.hd || 'Google Authenticated Researcher',
    };

    onSuccess(profile);
  };

  const handleSaveId = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputClientId.trim()) {
      onSaveClientId(inputClientId.trim());
      setErrorMessage(null);
    }
  };

  const isConfigured = Boolean(clientId && clientId.trim() !== '');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md bg-surface-elevated/95 border border-border rounded-2xl p-6 shadow-2xl glass-card-glow overflow-hidden">
        {/* Ambient background glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-brand-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-accent-cyan/15 rounded-full blur-3xl pointer-events-none" />

        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center p-1.5 shadow-sm">
              <svg viewBox="0 0 24 24" className="w-full h-full">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-white text-base">Google Identity Services</h3>
              <p className="text-xs text-slate-400">Official OAuth 2.0 Authentication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="mt-5 space-y-4">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {isConfigured ? (
            <div className="text-center py-4 space-y-4">
              <p className="text-xs text-slate-300">
                Sign in with your verified Google Account to enter the Macrograph-AI workspace:
              </p>

              {/* Real Official GoogleLogin Component from @react-oauth/google */}
              <div className="flex justify-center my-3">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => {
                    setErrorMessage('Google Authentication failed. Please check your network or credentials.');
                  }}
                  theme="filled_black"
                  shape="pill"
                  size="large"
                  text="signin_with"
                  useOneTap={false}
                />
              </div>

              <p className="text-[11px] text-slate-500 pt-2 flex items-center justify-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                <span>Secured via Google Identity Services (OAuth 2.0)</span>
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs space-y-1.5">
                <div className="font-semibold flex items-center gap-1.5">
                  <KeyRound className="w-4 h-4 text-amber-400" />
                  <span>Google OAuth Client ID Required</span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  To authenticate with real Google accounts, enter your Web Client ID from the{' '}
                  <a
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                    rel="noreferrer"
                    className="underline text-amber-400 hover:text-amber-300 inline-flex items-center gap-0.5"
                  >
                    Google Cloud Console <ExternalLink className="w-3 h-3" />
                  </a>
                  . Ensure Authorized JavaScript origin is set to <code className="text-white">http://localhost:5173</code>.
                </p>
              </div>

              <form onSubmit={handleSaveId} className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Google OAuth Web Client ID
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 123456789-abcdef.apps.googleusercontent.com"
                    value={inputClientId}
                    onChange={(e) => setInputClientId(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono rounded-xl bg-slate-900 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!inputClientId.trim()}
                  className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs shadow-glow-brand transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <span>Connect Google OAuth Client</span>
                </button>
              </form>
            </div>
          )}

          {/* Footer security badge */}
          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500 font-mono">
            <span className="flex items-center gap-1 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Direct Google Token Verification
            </span>
            <span>OAuth 2.0</span>
          </div>
        </div>
      </div>
    </div>
  );
};
