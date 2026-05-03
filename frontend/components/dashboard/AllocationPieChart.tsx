"use client"

import { useState } from "react"
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { PositionItem, PieSplit, buildPieSlices, colorForIndex } from "@/lib/dashboard"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const SPLIT_OPTIONS: { value: PieSplit; label: string }[] = [
  { value: "asset_class", label: "By Asset Class" },
  { value: "country", label: "By Country" },
  { value: "sector", label: "By Sector" },
  { value: "label", label: "By Label Group" },
  { value: "broker", label: "By Broker" },
]

interface AllocationPieChartProps {
  positions: PositionItem[]
  defaultSplit?: PieSplit
}

export function AllocationPieChart({ positions, defaultSplit = "asset_class" }: AllocationPieChartProps) {
  const [split, setSplit] = useState<PieSplit>(defaultSplit)

  const currencies = Array.from(new Set(positions.map((p) => p.currency))).sort()

  const allSlices = currencies.map((currency) => ({
    currency,
    slices: buildPieSlices(positions, split, currency),
    total: positions.filter((p) => p.currency === currency).reduce((s, p) => s + p.current_value, 0),
  }))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <span className="text-sm text-white/50">Split by</span>
        <Select value={split} onValueChange={(v) => setSplit(v as PieSplit)}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SPLIT_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-wrap gap-8">
        {allSlices.map(({ currency, slices, total }) => (
          <div key={currency} className="flex flex-col items-center gap-2">
            <p className="text-sm font-medium text-white/50">{currency}</p>
            <div className="h-64 w-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={40}
                    paddingAngle={2}
                  >
                    {slices.map((_, i) => (
                      <Cell key={`cell-${i}`} fill={colorForIndex(i)} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#0a0a0f",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value: number, name: string) => [
                      `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)} ${currency} (${total > 0 ? ((value / total) * 100).toFixed(1) : "0.0"}%)`,
                      name,
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
        {allSlices.length === 0 && (
          <p className="text-sm text-white/40">No position data.</p>
        )}
      </div>
    </div>
  )
}
