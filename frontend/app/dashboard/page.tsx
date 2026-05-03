import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"
import { Sidebar } from "@/components/dashboard/Sidebar"
import { SummaryBar } from "@/components/dashboard/SummaryBar"
import { PortfolioLineChart } from "@/components/dashboard/PortfolioLineChart"
import { AllocationPieChart } from "@/components/dashboard/AllocationPieChart"
import { SignOutButton } from "@/components/SignOutButton"
import {
  fetchSummary,
  fetchSnapshots,
  fetchTransactions,
  fetchPositions,
  SnapshotSeries,
} from "@/lib/dashboard"
import { fetchChartData } from "./actions"

function computeDailyChanges(seriesList: SnapshotSeries[]) {
  const oneDayMs = 24 * 60 * 60 * 1000
  const results: Array<{ currency: string; change_abs: number; change_pct: number }> = []

  for (const s of seriesList) {
    if (s.data.length < 2) continue
    const parts = s.name.split(" ")
    const currency = parts[parts.length - 1]
    const sorted = [...s.data].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )
    const latest = sorted[sorted.length - 1]
    const latestMs = new Date(latest.timestamp).getTime()

    let closest = sorted[0]
    let minDiff = Infinity
    for (const pt of sorted.slice(0, -1)) {
      const diff = Math.abs(latestMs - oneDayMs - new Date(pt.timestamp).getTime())
      if (diff < minDiff) { minDiff = diff; closest = pt }
    }

    const change_abs = latest.value - closest.value
    const change_pct = closest.value !== 0 ? (change_abs / closest.value) * 100 : 0
    results.push({ currency, change_abs, change_pct })
  }
  return results
}

export default async function DashboardPage() {
  const session = await auth()
  if (!session?.user) redirect("/")

  const token = (session as { backendToken?: string }).backendToken ?? ""

  const [summary, snapshots, transactions, positions] = await Promise.all([
    fetchSummary(token).catch(() => ({ accounts: [], last_synced_at: null })),
    fetchSnapshots(token, "1M", "total").catch(() => ({ series: [], currency_groups: [] })),
    fetchTransactions(token, "1M").catch(() => []),
    fetchPositions(token).catch(() => []),
  ])

  const dailyChanges = computeDailyChanges(snapshots.series)

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0a0f] text-white">
      <Sidebar />

      <main className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-3">
            {session.user.image && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={session.user.image}
                alt={session.user.name ?? ""}
                className="h-8 w-8 rounded-full"
              />
            )}
            <span className="text-sm text-white/60">{session.user.email}</span>
            <SignOutButton />
          </div>
        </div>

        {/* Summary bar */}
        <SummaryBar
          accounts={summary.accounts}
          lastSyncedAt={summary.last_synced_at}
          dailyChanges={dailyChanges}
        />

        {/* Line chart */}
        <section className="rounded-xl border border-white/8 bg-white/4 p-6">
          <h2 className="mb-4 text-lg font-semibold">Portfolio Performance</h2>
          <PortfolioLineChart
            initialSeries={snapshots.series}
            initialTransactions={transactions}
            defaultRange="1M"
            defaultSplit="total"
            onRangeChange={fetchChartData}
          />
        </section>

        {/* Pie chart */}
        <section className="rounded-xl border border-white/8 bg-white/4 p-6">
          <h2 className="mb-4 text-lg font-semibold">Capital Allocation</h2>
          <AllocationPieChart positions={positions} />
        </section>
      </main>
    </div>
  )
}
