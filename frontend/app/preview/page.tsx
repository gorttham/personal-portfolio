import { Sidebar } from "@/components/dashboard/Sidebar"
import { SummaryBar } from "@/components/dashboard/SummaryBar"
import { PortfolioLineChart } from "@/components/dashboard/PortfolioLineChart"
import { AllocationPieChart } from "@/components/dashboard/AllocationPieChart"
import { PositionsTable } from "@/components/dashboard/PositionsTable"
import type { SnapshotSeries, SnapshotRange, TransactionMarker, PositionItem } from "@/lib/dashboard"

// ── Sample data ───────────────────────────────────────────────────────────────

const ACCOUNTS = [
  { id: "1", broker: "ibkr", currency: "USD", total_value: 48250, account_name: "IBKR Main" },
  { id: "2", broker: "longbridge", currency: "HKD", total_value: 312000, account_name: "Longbridge HK" },
]

const DAILY_CHANGES = [
  { currency: "USD", change_abs: 620, change_pct: 1.3 },
  { currency: "HKD", change_abs: -1850, change_pct: -0.59 },
]

function makeDate(daysAgo: number) {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  d.setHours(16, 0, 0, 0)
  return d.toISOString()
}

const SERIES: SnapshotSeries[] = [
  {
    name: "Total USD",
    data: Array.from({ length: 30 }, (_, i) => ({
      timestamp: makeDate(29 - i),
      value: 42000 + Math.round(Math.sin(i / 3) * 1800 + i * 210 + Math.random() * 400),
    })),
  },
  {
    name: "Total HKD",
    data: Array.from({ length: 30 }, (_, i) => ({
      timestamp: makeDate(29 - i),
      value: 290000 + Math.round(Math.sin(i / 4) * 9000 + i * 750 + Math.random() * 2000),
    })),
  },
]

const TRANSACTIONS: TransactionMarker[] = [
  { ticker: "AAPL", type: "buy", quantity: 5, price: 178.4, executed_at: makeDate(22) },
  { ticker: "TSM", type: "buy", quantity: 200, price: 142.0, executed_at: makeDate(15) },
  { ticker: "NVDA", type: "sell", quantity: 3, price: 880.0, executed_at: makeDate(8) },
  { ticker: "700", type: "buy", quantity: 100, price: 325.0, executed_at: makeDate(4) },
]

const POSITIONS: PositionItem[] = [
  { ticker: "AAPL", name: "Apple Inc.", quantity: 52, avg_cost: 155.20, current_price: 181.10, current_value: 9420, unrealized_gain: 1346.8, unrealized_gain_pct: 16.69, currency: "USD", asset_class: "stock", sector: "Technology", country: "US", broker: "ibkr", label_names: ["Tech"] },
  { ticker: "NVDA", name: "NVIDIA Corp.", quantity: 14, avg_cost: 850.0, current_price: 903.50, current_value: 12650, unrealized_gain: 749.0, unrealized_gain_pct: 6.29, currency: "USD", asset_class: "stock", sector: "Technology", country: "US", broker: "ibkr", label_names: ["Tech", "AI"] },
  { ticker: "BRK.B", name: "Berkshire Hathaway", quantity: 30, avg_cost: 255.0, current_price: 270.0, current_value: 8100, unrealized_gain: 450.0, unrealized_gain_pct: 5.88, currency: "USD", asset_class: "stock", sector: "Financials", country: "US", broker: "ibkr", label_names: [] },
  { ticker: "GLD", name: "SPDR Gold ETF", quantity: 45, avg_cost: null, current_price: null, current_value: 7200, unrealized_gain: null, unrealized_gain_pct: null, currency: "USD", asset_class: "etf", sector: null, country: "US", broker: "ibkr", label_names: ["Safe Haven"] },
  { ticker: "TMUS", name: "T-Mobile US", quantity: 48, avg_cost: 135.0, current_price: 122.50, current_value: 5880, unrealized_gain: -600.0, unrealized_gain_pct: -9.26, currency: "USD", asset_class: "stock", sector: "Telecom", country: "US", broker: "ibkr", label_names: [] },
  { ticker: "700", name: "Tencent Holdings", quantity: 300, avg_cost: 310.0, current_price: 328.33, current_value: 98500, unrealized_gain: 5500.0, unrealized_gain_pct: 5.91, currency: "HKD", asset_class: "stock", sector: "Technology", country: "CN", broker: "longbridge", label_names: ["Tech"] },
  { ticker: "9988", name: "Alibaba Group", quantity: 600, avg_cost: 112.0, current_price: 120.0, current_value: 72000, unrealized_gain: 4800.0, unrealized_gain_pct: 7.14, currency: "HKD", asset_class: "stock", sector: "Consumer Cyclical", country: "CN", broker: "longbridge", label_names: [] },
  { ticker: "1299", name: "AIA Group", quantity: 1200, avg_cost: 48.0, current_price: 45.83, current_value: 55000, unrealized_gain: -2600.0, unrealized_gain_pct: -4.52, currency: "HKD", asset_class: "stock", sector: "Financials", country: "HK", broker: "longbridge", label_names: ["Dividend"] },
  { ticker: "2318", name: "Ping An Insurance", quantity: 800, avg_cost: 58.0, current_price: 60.0, current_value: 48000, unrealized_gain: 1600.0, unrealized_gain_pct: 3.45, currency: "HKD", asset_class: "stock", sector: "Financials", country: "CN", broker: "longbridge", label_names: ["Dividend"] },
  { ticker: "9618", name: "JD.com", quantity: 400, avg_cost: 90.0, current_price: 96.25, current_value: 38500, unrealized_gain: 2500.0, unrealized_gain_pct: 6.94, currency: "HKD", asset_class: "stock", sector: "Consumer Cyclical", country: "CN", broker: "longbridge", label_names: [] },
]

// ── No-op chart fetcher for preview (returns same data) ───────────────────────

async function noopFetcher() {
  "use server"
  return { series: SERIES, transactions: TRANSACTIONS }
}

async function noopBenchmarkFetcher(
  symbol: "SPX" | "HSI",
  _range: SnapshotRange
): Promise<SnapshotSeries> {
  "use server"
  const spxData = Array.from({ length: 30 }, (_, i) => ({
    timestamp: makeDate(29 - i),
    value: 5000 + Math.round(Math.sin(i / 3.5) * 150 + i * 12),
  }))
  const hsiData = Array.from({ length: 30 }, (_, i) => ({
    timestamp: makeDate(29 - i),
    value: 19200 + Math.round(Math.sin(i / 4) * 400 + i * 25),
  }))
  return symbol === "SPX"
    ? { name: "S&P 500", data: spxData }
    : { name: "Hang Seng", data: hsiData }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function PreviewPage() {
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--background)] text-[var(--text-primary)]">
      <Sidebar />
      <main className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-xs text-white/30 mt-0.5">Preview mode — sample data</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-[#6366f1] flex items-center justify-center text-sm font-semibold">G</div>
            <span className="text-sm text-white/60">demo@example.com</span>
          </div>
        </div>

        <SummaryBar
          accounts={ACCOUNTS}
          lastSyncedAt={makeDate(0)}
          dailyChanges={DAILY_CHANGES}
        />

        <section className="rounded-xl border border-black/8 dark:border-white/8 bg-[var(--surface)] p-6">
          <h2 className="mb-4 text-lg font-semibold">Portfolio Performance</h2>
          <PortfolioLineChart
            initialSeries={SERIES}
            initialTransactions={TRANSACTIONS}
            defaultRange="1M"
            defaultSplit="total"
            onRangeChange={noopFetcher}
            onBenchmarkFetch={noopBenchmarkFetcher}
          />
        </section>

        <section className="rounded-xl border border-black/8 dark:border-white/8 bg-[var(--surface)] p-6">
          <h2 className="mb-4 text-lg font-semibold">Capital Allocation</h2>
          <AllocationPieChart positions={POSITIONS} />
        </section>

        <section className="rounded-xl border border-black/8 dark:border-white/8 bg-[var(--surface)] p-6">
          <h2 className="mb-4 text-lg font-semibold">Positions &amp; P&L</h2>
          <PositionsTable positions={POSITIONS} />
        </section>
      </main>
    </div>
  )
}
