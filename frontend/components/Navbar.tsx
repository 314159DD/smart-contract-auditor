"use client";

import Link from "next/link";
import { Shield, LayoutDashboard, LogOut, LogIn, Zap } from "lucide-react";
import { useAuth } from "@/lib/auth";

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="border-b border-surface-5/60 bg-surface-0/70 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative">
            <Shield className="w-5 h-5 text-terminal-green transition-all group-hover:drop-shadow-[0_0_8px_rgba(0,255,65,0.4)]" />
            <div className="absolute inset-0 bg-terminal-green/20 blur-md rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <span className="font-display font-bold text-white tracking-tight">
            ContractAudit
          </span>
          <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono font-medium text-terminal-green border border-terminal-green/20 rounded bg-terminal-green/5 uppercase tracking-wider">
            AI
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/pricing"
            className="text-sm text-neutral-500 hover:text-neutral-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.03] hidden sm:block"
          >
            Pricing
          </Link>

          {user ? (
            <>
              <Link
                href="/dashboard"
                className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.03]"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="hidden sm:block">Dashboard</span>
              </Link>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 text-sm text-neutral-600 hover:text-neutral-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.03]"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:block">Sign out</span>
              </button>
            </>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="text-sm text-neutral-500 hover:text-neutral-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.03] hidden sm:block"
              >
                Log in
              </Link>
              <Link
                href="/auth/login"
                className="flex items-center gap-1.5 text-sm font-medium bg-terminal-green/10 hover:bg-terminal-green/15 text-terminal-green border border-terminal-green/20 hover:border-terminal-green/30 px-3.5 py-1.5 rounded-lg transition-all btn-lift"
              >
                <Zap className="w-3.5 h-3.5" />
                Start Scanning
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
