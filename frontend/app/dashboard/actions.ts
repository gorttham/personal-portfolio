"use server"

import { auth } from "@/lib/auth"
import { fetchSnapshots, fetchTransactions, fetchBenchmark, SnapshotRange, SnapshotSplit, SnapshotSeries, TransactionMarker } from "@/lib/dashboard"

export async function fetchChartData(
  range: SnapshotRange,
  split: SnapshotSplit,
): Promise<{ series: SnapshotSeries[]; transactions: TransactionMarker[] }> {
  const session = await auth()
  if (!session) throw new Error("Not authenticated")
  const token = (session as { backendToken?: string }).backendToken ?? ""
  const [snapshots, transactions] = await Promise.all([
    fetchSnapshots(token, range, split),
    fetchTransactions(token, range),
  ])
  return { series: snapshots.series, transactions }
}

export async function fetchBenchmarkData(
  symbol: "SPX" | "HSI",
  range: SnapshotRange,
): Promise<SnapshotSeries> {
  "use server"
  const session = await auth()
  if (!session?.user) throw new Error("Not authenticated")
  const token = (session as { backendToken?: string }).backendToken ?? ""
  return fetchBenchmark(token, symbol, range)
}
