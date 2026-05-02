import { redirect } from "next/navigation"
import Link from "next/link"
import { auth } from "@/lib/auth"
import { SignOutButton } from "@/components/SignOutButton"

export default async function DashboardPage() {
  const session = await auth()

  if (!session) {
    redirect("/")
  }

  const user = session.user
  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? "?"

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white flex flex-col">
      {/* Top bar */}
      <header className="border-b border-white/10 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-base font-semibold tracking-tight">
            Portfolio Tracker
          </span>

          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className="flex items-center gap-2">
              {user?.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={user.image}
                  alt={user.name ?? "User avatar"}
                  className="w-7 h-7 rounded-full object-cover ring-1 ring-white/20"
                />
              ) : (
                <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-xs font-semibold">
                  {initials}
                </div>
              )}
              <span className="text-sm text-white/70 hidden sm:block">
                {user?.email}
              </span>
            </div>

            <SignOutButton />
          </div>
        </div>
      </header>

      {/* Summary bar */}
      <div className="border-b border-white/5 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6 text-sm text-white/50">
          <span>
            Portfolio value{" "}
            <span className="text-white/30 font-mono">—</span>
          </span>
          <span className="text-white/20">·</span>
          <span>Last synced: —</span>
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-16">
        <div className="flex flex-col items-center justify-center text-center gap-6">
          {/* Empty state icon */}
          <div className="w-16 h-16 rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center text-3xl">
            📈
          </div>

          <div>
            <h2 className="text-xl font-semibold text-white mb-2">
              No brokerages connected
            </h2>
            <p className="text-white/50 text-sm max-w-sm">
              Connect your brokerage accounts to start tracking your portfolio
              in one place.
            </p>
          </div>

          <Link
            href="/connect"
            className="inline-flex items-center justify-center h-9 px-5 rounded-lg text-sm font-medium bg-accent hover:bg-[#4f46e5] text-white transition-colors"
          >
            Connect your brokerages
          </Link>
        </div>

        {/* Placeholder grid */}
        <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {["Total value", "Today's change", "Open positions"].map((label) => (
            <div
              key={label}
              className="rounded-xl border border-white/10 bg-white/5 p-6"
            >
              <p className="text-xs text-white/40 uppercase tracking-wider mb-2">
                {label}
              </p>
              <p className="text-2xl font-semibold text-white/20 font-mono">
                —
              </p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
