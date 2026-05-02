"use client"

import { signIn } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const features = [
  {
    icon: "⚡",
    title: "Real-time sync",
    description:
      "Live position and P&L updates across all your brokerage accounts simultaneously.",
  },
  {
    icon: "🤖",
    title: "AI insights",
    description:
      "Chat with your portfolio — ask anything about performance, risk, or allocation.",
  },
  {
    icon: "📊",
    title: "Unified dashboard",
    description:
      "One view for Moomoo, Longbridge, and IBKR. No more tab-switching.",
  },
  {
    icon: "🏷️",
    title: "Custom labels",
    description:
      "Tag and group holdings your way — by strategy, sector, or any label you create.",
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-white flex flex-col">
      {/* Ambient glow */}
      <div
        className="pointer-events-none fixed inset-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full bg-accent/10 blur-[120px]" />
      </div>

      {/* Nav */}
      <header className="relative z-10 flex items-center justify-between px-6 py-5 max-w-6xl mx-auto w-full">
        <span className="text-lg font-semibold tracking-tight text-white">
          Portfolio Tracker
        </span>
        <button
          onClick={() => signIn()}
          className="text-sm text-white/60 hover:text-white transition-colors"
        >
          Sign in
        </button>
      </header>

      {/* Hero */}
      <main className="relative z-10 flex flex-col items-center justify-center flex-1 text-center px-4 pt-16 pb-24">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs text-white/60 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-accent inline-block" />
          Moomoo · Longbridge · IBKR
        </div>

        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Track all your brokerages{" "}
          <span className="text-accent">in one place</span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-white/50 max-w-xl leading-relaxed">
          Aggregate positions from Moomoo, Longbridge, and IBKR. Get a unified
          view of your portfolio and chat with AI to surface insights
          instantly.
        </p>

        {/* Sign-in buttons */}
        <div className="mt-10 flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
            className={cn(
              "inline-flex items-center justify-center gap-3 h-11 px-6 rounded-lg text-sm font-medium transition-colors",
              "border border-white/20 bg-white/5 hover:bg-white/10 text-white"
            )}
          >
            <GoogleIcon />
            Continue with Google
          </button>

          <button
            onClick={() => signIn("github", { callbackUrl: "/dashboard" })}
            className={cn(
              "inline-flex items-center justify-center gap-3 h-11 px-6 rounded-lg text-sm font-medium transition-colors",
              "bg-white/10 hover:bg-white/15 text-white border border-white/10"
            )}
          >
            <GitHubIcon />
            Continue with GitHub
          </button>
        </div>

        <p className="mt-4 text-xs text-white/30">
          No credit card required. Free to start.
        </p>

        {/* Feature grid */}
        <div className="mt-24 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl w-full px-2">
          {features.map((f) => (
            <Card
              key={f.title}
              className="bg-white/5 border border-white/10 rounded-xl text-left hover:border-white/20 transition-colors"
            >
              <CardContent className="p-6">
                <div className="text-2xl mb-3">{f.icon}</div>
                <h3 className="font-semibold text-white text-sm mb-1">
                  {f.title}
                </h3>
                <p className="text-xs text-white/50 leading-relaxed">
                  {f.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 text-center py-6 text-xs text-white/20 border-t border-white/5">
        © {new Date().getFullYear()} Portfolio Tracker
      </footer>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}
