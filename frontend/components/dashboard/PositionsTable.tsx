"use client"

import { useState } from "react"
import { PositionItem } from "@/lib/dashboard"

interface PositionsTableProps {
  positions: PositionItem[]
}

function formatQty(value: number | null): string {
  if (value === null) return "—"
  // Up to 4 decimal places, strip trailing zeros
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 4,
  }).format(value)
}

function formatPrice(value: number | null, currency: string): string {
  if (value === null) return "—"
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${value.toFixed(2)} ${currency}`
  }
}

function formatCompactValue(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)
  } catch {
    return `${(value / 1000).toFixed(1)}K ${currency}`
  }
}

function formatGain(value: number | null, currency: string): string {
  if (value === null) return "—"
  const sign = value >= 0 ? "+" : ""
  try {
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Math.abs(value))
    return `${sign}${value < 0 ? "-" : ""}${formatted.replace(/^-/, "")}`
  } catch {
    return `${sign}${value.toFixed(0)} ${currency}`
  }
}

function formatGainPct(value: number | null): string {
  if (value === null) return "—"
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(2)}%`
}

function gainColor(value: number | null): string {
  if (value === null) return "text-white/30"
  return value >= 0 ? "text-emerald-400" : "text-red-400"
}

export function PositionsTable({ positions }: PositionsTableProps) {
  const currencies = Array.from(new Set(positions.map((p) => p.currency))).sort()
  const defaultCurrency = currencies.includes("USD") ? "USD" : (currencies[0] ?? "USD")
  const [selectedCurrency, setSelectedCurrency] = useState<string>(defaultCurrency)

  const filtered = positions.filter((p) => p.currency === selectedCurrency)

  const totalGain = filtered.reduce<number | null>((acc, p) => {
    if (p.unrealized_gain === null) return acc
    return (acc ?? 0) + p.unrealized_gain
  }, null)

  return (
    <div className="flex flex-col gap-4">
      {/* Currency selector — only shown if multiple currencies */}
      {currencies.length > 1 && (
        <div className="flex gap-2">
          {currencies.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCurrency(c)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                c === selectedCurrency
                  ? "bg-white/10 text-white"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse">
          <thead>
            <tr>
              <th className="text-left text-xs uppercase text-white/40 pb-2 pr-4">Ticker</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 px-4">Qty</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 px-4">Avg Cost</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 px-4">Price</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 px-4">Value</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 px-4">Gain/Loss</th>
              <th className="text-right text-xs uppercase text-white/40 pb-2 pl-4">%</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((pos) => (
              <tr
                key={`${pos.ticker}-${pos.broker}`}
                className="border-t border-white/5 hover:bg-white/[0.02] transition-colors"
              >
                {/* Ticker + Name */}
                <td className="py-3 pr-4">
                  <span className="font-semibold text-white">{pos.ticker}</span>
                  <br />
                  <span className="text-xs text-white/40">{pos.name}</span>
                </td>
                {/* Qty */}
                <td className="py-3 px-4 text-right tabular-nums text-sm text-white/70">
                  {formatQty(pos.quantity)}
                </td>
                {/* Avg Cost */}
                <td className="py-3 px-4 text-right tabular-nums text-sm text-white/70">
                  {formatPrice(pos.avg_cost, selectedCurrency)}
                </td>
                {/* Price */}
                <td className="py-3 px-4 text-right tabular-nums text-sm text-white/70">
                  {formatPrice(pos.current_price, selectedCurrency)}
                </td>
                {/* Value */}
                <td className="py-3 px-4 text-right tabular-nums text-sm text-white">
                  {formatCompactValue(pos.current_value, selectedCurrency)}
                </td>
                {/* Gain/Loss */}
                <td className={`py-3 px-4 text-right tabular-nums text-sm font-medium ${gainColor(pos.unrealized_gain)}`}>
                  {formatGain(pos.unrealized_gain, selectedCurrency)}
                </td>
                {/* % */}
                <td className={`py-3 pl-4 text-right tabular-nums text-sm font-medium ${gainColor(pos.unrealized_gain_pct)}`}>
                  {formatGainPct(pos.unrealized_gain_pct)}
                </td>
              </tr>
            ))}
          </tbody>
          {/* Footer: total unrealized gain */}
          <tfoot>
            <tr className="border-t border-white/10">
              <td colSpan={5} className="py-3 pr-4 text-xs text-white/40 uppercase">
                Total Unrealized Gain
              </td>
              <td className={`py-3 px-4 text-right tabular-nums text-sm font-semibold ${gainColor(totalGain)}`}>
                {formatGain(totalGain, selectedCurrency)}
              </td>
              <td className="py-3 pl-4" />
            </tr>
          </tfoot>
        </table>

        {filtered.length === 0 && (
          <p className="py-8 text-center text-sm text-white/40">No positions for {selectedCurrency}.</p>
        )}
      </div>
    </div>
  )
}
