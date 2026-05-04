import { AccountSummary } from "@/lib/dashboard"

interface DailyChange {
  currency: string
  change_abs: number
  change_pct: number
}

interface SummaryBarProps {
  accounts: AccountSummary[]
  lastSyncedAt: string | null
  dailyChanges: DailyChange[]
}

function formatCurrency(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value)
  } catch {
    return `${value.toFixed(0)} ${currency}`
  }
}

function formatPct(value: number): string {
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(2)}%`
}

function formatSyncAge(isoString: string): string {
  const ms = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function SummaryBar({ accounts, lastSyncedAt, dailyChanges }: SummaryBarProps) {
  const byCurrency = accounts.reduce<Record<string, number>>((acc, a) => {
    acc[a.currency] = (acc[a.currency] ?? 0) + a.total_value
    return acc
  }, {})

  const currencies = Object.entries(byCurrency).sort(([a], [b]) => a.localeCompare(b))

  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-black/8 dark:border-white/8 bg-[var(--surface)] px-6 py-4">
      {currencies.map(([currency, total]) => {
        const change = dailyChanges.find((d) => d.currency === currency)
        const isPositive = !change || change.change_abs >= 0
        return (
          <div key={currency} className="flex flex-col">
            <span className="text-xs text-black/50 dark:text-white/50">{currency} Total</span>
            <span className="text-xl font-semibold tabular-nums text-black dark:text-white">
              {formatCurrency(total, currency)}
            </span>
            {change && (
              <span
                className={`text-sm font-medium tabular-nums ${
                  isPositive ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {formatCurrency(change.change_abs, currency)} ({formatPct(change.change_pct)})
              </span>
            )}
          </div>
        )
      })}

      <div className="flex-1" />

      <div className="flex flex-col items-end gap-1">
        <div
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            lastSyncedAt
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {lastSyncedAt ? "Synced" : "Never synced"}
        </div>
        {lastSyncedAt && (
          <span className="text-xs text-black/40 dark:text-white/40">
            Last synced {formatSyncAge(lastSyncedAt)}
          </span>
        )}
      </div>
    </div>
  )
}
