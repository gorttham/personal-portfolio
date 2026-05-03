"use client"

import { useState, useCallback } from "react"
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  SnapshotSeries,
  TransactionMarker,
  SnapshotRange,
  SnapshotSplit,
  normalizeToPercent,
  colorForIndex,
} from "@/lib/dashboard"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const RANGES: { value: SnapshotRange; label: string }[] = [
  { value: "1W", label: "1W" },
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "6M", label: "6M" },
  { value: "1Y", label: "1Y" },
  { value: "all", label: "All" },
]

const SPLITS: { value: SnapshotSplit; label: string }[] = [
  { value: "total", label: "Total" },
  { value: "broker", label: "By Broker" },
  { value: "label", label: "By Label" },
  { value: "stock", label: "By Stock" },
]

const BENCHMARK_LABELS: Record<"SPX" | "HSI", string> = {
  SPX: "S&P 500",
  HSI: "Hang Seng",
}

const BENCHMARK_COLORS = ["rgba(255,255,255,0.45)", "rgba(251,191,36,0.45)"]

interface MarkerShapeProps {
  cx?: number
  cy?: number
  payload?: TransactionMarker & { value?: number }
}

function TradeMarkerShape({ cx = 0, cy = 0, payload }: MarkerShapeProps) {
  if (!payload) return null
  const isBuy = payload.type === "buy"
  const color = isBuy ? "#10b981" : "#ef4444"
  const path = isBuy
    ? `M ${cx} ${cy - 8} L ${cx + 6} ${cy + 4} L ${cx - 6} ${cy + 4} Z`
    : `M ${cx} ${cy + 8} L ${cx + 6} ${cy - 4} L ${cx - 6} ${cy - 4} Z`
  return <path d={path} fill={color} stroke="none" />
}

interface PortfolioLineChartProps {
  initialSeries: SnapshotSeries[]
  initialTransactions: TransactionMarker[]
  defaultRange?: SnapshotRange
  defaultSplit?: SnapshotSplit
  onRangeChange: (range: SnapshotRange, split: SnapshotSplit) => Promise<{
    series: SnapshotSeries[]
    transactions: TransactionMarker[]
  }>
  onBenchmarkFetch?: (symbol: "SPX" | "HSI", range: SnapshotRange) => Promise<SnapshotSeries>
}

export function PortfolioLineChart({
  initialSeries,
  initialTransactions,
  defaultRange = "1M",
  defaultSplit = "total",
  onRangeChange,
  onBenchmarkFetch,
}: PortfolioLineChartProps) {
  const [series, setSeries] = useState<SnapshotSeries[]>(initialSeries)
  const [transactions, setTransactions] = useState<TransactionMarker[]>(initialTransactions)
  const [range, setRange] = useState<SnapshotRange>(defaultRange)
  const [split, setSplit] = useState<SnapshotSplit>(defaultSplit)
  const [yMode, setYMode] = useState<"absolute" | "percent">("absolute")
  const [loading, setLoading] = useState(false)
  const [activeBenchmarks, setActiveBenchmarks] = useState<Set<"SPX" | "HSI">>(new Set())
  const [benchmarkCache, setBenchmarkCache] = useState<Map<string, SnapshotSeries>>(new Map())
  const [benchmarkLoading, setBenchmarkLoading] = useState(false)

  const handleControlChange = useCallback(
    async (newRange: SnapshotRange, newSplit: SnapshotSplit) => {
      setLoading(true)
      setActiveBenchmarks(new Set())
      setBenchmarkCache(new Map())
      setBenchmarkLoading(false)
      try {
        const result = await onRangeChange(newRange, newSplit)
        setSeries(result.series)
        setTransactions(result.transactions)
        setRange(newRange)
        setSplit(newSplit)
      } finally {
        setLoading(false)
      }
    },
    [onRangeChange],
  )

  const handleBenchmarkToggle = useCallback(async (symbol: "SPX" | "HSI") => {
    if (!onBenchmarkFetch) return
    const cacheKey = `${symbol}:${range}`
    const next = new Set(activeBenchmarks)

    if (next.has(symbol)) {
      next.delete(symbol)
      setActiveBenchmarks(next)
      return
    }

    if (!benchmarkCache.has(cacheKey)) {
      setBenchmarkLoading(true)
      try {
        const result = await onBenchmarkFetch(symbol, range)
        setBenchmarkCache(prev => new Map(prev).set(cacheKey, result))
        setActiveBenchmarks(prev => new Set(prev).add(symbol))
      } finally {
        setBenchmarkLoading(false)
      }
    } else {
      setActiveBenchmarks(prev => new Set(prev).add(symbol))
    }
  }, [activeBenchmarks, benchmarkCache, range, onBenchmarkFetch])

  const activeSeries = series.map((s) => ({
    ...s,
    data: yMode === "percent" ? normalizeToPercent(s.data) : s.data,
  }))

  const benchmarkDisplaySeries = yMode === "percent"
    ? Array.from(activeBenchmarks)
        .map(sym => {
          const cacheKey = `${sym}:${range}`
          const s = benchmarkCache.get(cacheKey)
          return s ? { ...s, name: BENCHMARK_LABELS[sym] } : null
        })
        .filter(Boolean) as SnapshotSeries[]
    : []

  const allSeries = [...activeSeries, ...benchmarkDisplaySeries]

  const timestampSet = new Set<string>()
  for (const s of allSeries) {
    for (const pt of s.data) timestampSet.add(pt.timestamp)
  }
  const sortedTimestamps = Array.from(timestampSet).sort()

  const chartData = sortedTimestamps.map((ts) => {
    const point: Record<string, number | string> = { timestamp: ts }
    for (const s of allSeries) {
      const match = s.data.find((d) => d.timestamp === ts)
      if (match !== undefined) point[s.name] = match.value
    }
    return point
  })

  const scatterData = transactions.map((t) => {
    const tsMs = new Date(t.executed_at).getTime()
    let closest = sortedTimestamps[0] ?? ""
    let minDiff = Infinity
    for (const ts of sortedTimestamps) {
      const diff = Math.abs(new Date(ts).getTime() - tsMs)
      if (diff < minDiff) { minDiff = diff; closest = ts }
    }
    const seriesPoint = activeSeries[0]?.data.find((d) => d.timestamp === closest)
    return { timestamp: closest, value: seriesPoint?.value ?? 0, ...t }
  })

  const formatDate = (v: string) => {
    try { return new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }
    catch { return v }
  }

  const formatValue = (v: number) =>
    yMode === "percent"
      ? `${v.toFixed(1)}%`
      : new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-md border border-white/10">
          {RANGES.map((r) => (
            <button
              key={r.value}
              onClick={() => handleControlChange(r.value, split)}
              disabled={loading}
              className={`px-3 py-1 text-sm transition-colors first:rounded-l-md last:rounded-r-md ${
                range === r.value
                  ? "bg-[#6366f1] text-white"
                  : "text-white/50 hover:bg-white/5"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        <Select
          value={split}
          onValueChange={(v) => handleControlChange(range, v as SnapshotSplit)}
          disabled={loading}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SPLITS.map((s) => (
              <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex rounded-md border border-white/10">
          {(["absolute", "percent"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setYMode(mode)}
              className={`px-3 py-1 text-sm first:rounded-l-md last:rounded-r-md ${
                yMode === mode ? "bg-[#6366f1] text-white" : "text-white/50 hover:bg-white/5"
              }`}
            >
              {mode === "absolute" ? "$" : "%"}
            </button>
          ))}
        </div>

        {onBenchmarkFetch && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-white/30">vs</span>
            {(["SPX", "HSI"] as const).map(sym => (
              <button
                key={sym}
                onClick={() => handleBenchmarkToggle(sym)}
                disabled={yMode === "absolute" || loading || benchmarkLoading}
                title={yMode === "absolute" ? "Switch to % mode to compare benchmarks" : undefined}
                className={`px-2 py-1 text-xs rounded border transition-colors ${
                  activeBenchmarks.has(sym) && yMode === "percent"
                    ? "border-white/30 bg-white/10 text-white/60"
                    : "border-white/10 text-white/30 hover:text-white/50 disabled:opacity-30 disabled:cursor-not-allowed"
                }`}
              >
                {sym}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className={`h-80 transition-opacity ${loading ? "opacity-40" : ""}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatDate}
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.4)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.4)" }}
              tickFormatter={formatValue}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: "#0a0a0f",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelFormatter={(v: string) => {
                try { return new Date(v).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) }
                catch { return v }
              }}
              formatter={(value: number, name: string) => [
                yMode === "percent" ? `${value.toFixed(2)}%` : new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value),
                name,
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
            />
            {activeSeries.map((s, i) => (
              <Line
                key={s.name}
                type="monotone"
                dataKey={s.name}
                stroke={colorForIndex(i)}
                dot={false}
                strokeWidth={2}
                connectNulls
              />
            ))}
            {benchmarkDisplaySeries.map((s, i) => (
              <Line
                key={`bm-${s.name}`}
                type="monotone"
                dataKey={s.name}
                stroke={BENCHMARK_COLORS[i % BENCHMARK_COLORS.length]}
                dot={false}
                strokeWidth={1.5}
                strokeDasharray="5 5"
                connectNulls
              />
            ))}
            <Scatter
              data={scatterData}
              dataKey="value"
              shape={(props: MarkerShapeProps) => <TradeMarkerShape {...props} />}
              legendType="none"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
