"use client"

import * as React from "react"
import { apiFetchRaw } from "@/lib/api"
import { BrokerCard } from "@/components/connect/BrokerCard"

interface BrokerConnection {
  id: string
  broker: string
  status: string
  last_synced_at: string | null
}

interface ConnectPageClientProps {
  backendToken: string
}

const BROKER_ORDER = ["moomoo", "longbridge", "ibkr"] as const

function ConnectionsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {BROKER_ORDER.map((b) => (
        <div
          key={b}
          className="h-48 rounded-xl border border-white/8 bg-white/4 animate-pulse"
        />
      ))}
    </div>
  )
}

export function ConnectPageClient({ backendToken }: ConnectPageClientProps) {
  const [connections, setConnections] = React.useState<BrokerConnection[]>([])
  const [loading, setLoading] = React.useState(true)
  const [fetchError, setFetchError] = React.useState<string | null>(null)

  async function loadConnections() {
    setLoading(true)
    setFetchError(null)
    try {
      const res = await apiFetchRaw("/brokerages", backendToken)
      if (!res.ok) {
        throw new Error(`Failed to load connections (${res.status})`)
      }
      const data: BrokerConnection[] = await res.json()
      setConnections(data)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Failed to load connections.")
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => {
    loadConnections()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleConnect(broker: string, credentials: string) {
    const res = await apiFetchRaw("/brokerages/connect", backendToken, {
      method: "POST",
      body: JSON.stringify({ broker, credentials }),
    })
    if (!res.ok) {
      const body = await res.text()
      throw new Error(body || `Connection failed (${res.status})`)
    }
    await loadConnections()
  }

  async function handleDisconnect(id: string) {
    const res = await apiFetchRaw(`/brokerages/${id}`, backendToken, {
      method: "DELETE",
    })
    if (!res.ok) {
      const body = await res.text()
      throw new Error(body || `Disconnect failed (${res.status})`)
    }
    await loadConnections()
  }

  function getConnection(broker: string): { id: string; status: string; last_synced_at: string | null } | undefined {
    return connections.find((c: BrokerConnection) => c.broker === broker)
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center">
          <span className="text-base font-semibold tracking-tight">
            Portfolio Tracker
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">
            Connect Brokerages
          </h1>
          <p className="text-white/50 text-sm">
            Link your brokerage accounts to track your portfolio in one place.
          </p>
        </div>

        {/* Error state */}
        {fetchError && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 flex items-center justify-between gap-4">
            <span>{fetchError}</span>
            <button
              onClick={loadConnections}
              className="shrink-0 underline underline-offset-2 hover:text-red-300 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Cards */}
        {loading ? (
          <ConnectionsSkeleton />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {BROKER_ORDER.map((broker) => (
              <BrokerCard
                key={broker}
                broker={broker}
                connection={getConnection(broker)}
                backendToken={backendToken}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
