import { apiFetch } from "./api"

export interface AccountSummary {
  id: string
  broker: string
  currency: string
  total_value: number
  account_name: string
}

export interface PortfolioSummary {
  accounts: AccountSummary[]
  last_synced_at: string | null
}

export interface SnapshotPoint {
  timestamp: string
  value: number
}

export interface SnapshotSeries {
  name: string
  data: SnapshotPoint[]
}

export interface PortfolioSnapshots {
  series: SnapshotSeries[]
  currency_groups: string[]
}

export type SnapshotRange = "1W" | "1M" | "3M" | "6M" | "1Y" | "all"
export type SnapshotSplit = "total" | "broker" | "label" | "stock"

export interface TransactionMarker {
  ticker: string
  type: "buy" | "sell"
  quantity: number
  price: number
  executed_at: string
}

export interface PositionItem {
  ticker: string
  name: string
  quantity: number | null
  avg_cost: number | null
  current_price: number | null
  current_value: number
  unrealized_gain: number | null
  unrealized_gain_pct: number | null
  currency: string
  asset_class: string
  sector: string | null
  country: string | null
  broker: string
  label_names: string[]
}

export type PieSplit = "asset_class" | "country" | "sector" | "label" | "broker"

export const CHART_COLORS = [
  "#6366f1",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
]

export function colorForIndex(i: number): string {
  return CHART_COLORS[i % CHART_COLORS.length]
}

export function normalizeToPercent(data: SnapshotPoint[]): SnapshotPoint[] {
  if (data.length === 0) return []
  const base = data[0].value
  if (base === 0) return data.map((p) => ({ ...p, value: 0 }))
  return data.map((p) => ({
    timestamp: p.timestamp,
    value: ((p.value / base) - 1) * 100,
  }))
}

export interface PieSlice {
  name: string
  value: number
  currency: string
}

export function buildPieSlices(
  positions: PositionItem[],
  split: PieSplit,
  currency: string,
): PieSlice[] {
  const filtered = positions.filter((p) => p.currency === currency)
  const map = new Map<string, number>()

  for (const pos of filtered) {
    let key: string
    switch (split) {
      case "asset_class":
        key = pos.asset_class || "Unknown"
        break
      case "country":
        key = pos.country || "Unknown"
        break
      case "sector":
        key = pos.sector || "Unknown"
        break
      case "label":
        if (pos.label_names.length === 0) {
          key = "Unassigned"
        } else {
          const share = pos.current_value / pos.label_names.length
          for (const label of pos.label_names) {
            map.set(label, (map.get(label) ?? 0) + share)
          }
          continue
        }
        break
      case "broker":
        key = pos.broker
        break
      default:
        key = "Unknown"
    }
    map.set(key, (map.get(key) ?? 0) + pos.current_value)
  }

  return Array.from(map.entries())
    .map(([name, value]) => ({ name, value, currency }))
    .sort((a, b) => b.value - a.value)
}

export async function fetchSummary(token: string): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>("/portfolio/summary", {}, token)
}

export async function fetchSnapshots(
  token: string,
  range: SnapshotRange,
  split: SnapshotSplit,
): Promise<PortfolioSnapshots> {
  return apiFetch<PortfolioSnapshots>(
    `/portfolio/snapshots?range=${range}&split=${split}`,
    {},
    token,
  )
}

export async function fetchTransactions(
  token: string,
  range: SnapshotRange,
): Promise<TransactionMarker[]> {
  return apiFetch<TransactionMarker[]>(
    `/portfolio/transactions?range=${range}`,
    {},
    token,
  )
}

export async function fetchPositions(token: string): Promise<PositionItem[]> {
  return apiFetch<PositionItem[]>("/portfolio/positions", {}, token)
}
