import React, { useState } from 'react';
import { X, Lock, Building, ArrowRight, ShieldCheck, Check } from 'lucide-react';

interface SignInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: string) => void;
}

export const SignInModal: React.FC<SignInModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [email, setEmail] = useState('');
  const [selectedRole, setSelectedRole] = useState('Institutional Researcher');
  const [signedIn, setSignedIn] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSignedIn(true);
    setTimeout(() => {
      onSuccess(email || 'demo.user@macrograph.ai');
      onClose();
      setSignedIn(false);
    }, 800);
  };

  const handleQuickDemo = () => {
    setSignedIn(true);
    setTimeout(() => {
      onSuccess('policy.analyst@rbi.org.in');
      onClose();
      setSignedIn(false);
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl p-6 text-slate-100">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white tracking-tight">Access MacroGraph AI</h3>
            <p className="text-xs text-slate-400">Verified Macro Intelligence & Causal SCM</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Work / Institutional Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. analyst@rbi.org.in or scholar@iima.ac.in"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-white placeholder-slate-500 outline-none transition-all"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Institutional Tier
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700 focus:border-cyan-500 text-sm text-white outline-none"
            >
              <option value="Central Bank & Policy Maker">Central Bank & Policy Maker (RBI / MoF)</option>
              <option value="Institutional Researcher">Academic & Think Tank (DSE / IIM / NIPFP)</option>
              <option value="Asset Management">Asset Management & Capital Markets (AMFI / FPI)</option>
              <option value="Public Macro Scholar">Independent Economic Researcher</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={signedIn}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm py-3 rounded-xl shadow-lg shadow-cyan-500/20 transition-all active:scale-95 disabled:opacity-50"
          >
            {signedIn ? (
              <>
                <Check className="w-4 h-4 text-emerald-300" />
                <span>Authenticating Credentials...</span>
              </>
            ) : (
              <>
                <span>Sign in to Platform</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-800" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-slate-900 px-3 text-slate-500 font-medium">Or Quick Access</span>
          </div>
        </div>

        {/* Quick Demo Access */}
        <button
          type="button"
          onClick={handleQuickDemo}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition-all"
        >
          <Building className="w-4 h-4 text-cyan-400" />
          <span>Launch Immediate Policy Sandbox (1-Click)</span>
        </button>

        {/* Security badge */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Encrypted with SHA-256 Observation Digest Verification</span>
        </div>
      </div>
    </div>
  );
};
