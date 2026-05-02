"use client"

import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { TokenDrawer } from "@/components/connect/TokenDrawer"
import { cn } from "@/lib/utils"

// NEXT_PUBLIC_ env vars are inlined by Next.js at build time.
// Declaring via a cast avoids requiring @types/node in the tsconfig.
declare const __NEXT_PUBLIC_ENV__: never
void (typeof __NEXT_PUBLIC_ENV__)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const API_BASE_URL: string = (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface BrokerCardProps {
  broker: "moomoo" | "longbridge" | "ibkr"
  connection?: { id: string; status: string; last_synced_at: string | null }
  backendToken: string
  onConnect: (broker: string, credentials: string) => Promise<void>
  onDisconnect: (id: string) => Promise<void>
}

const BROKER_META: Record<
  BrokerCardProps["broker"],
  { name: string; description: string; color: string; initial: string }
> = {
  moomoo: {
    name: "Moomoo",
    description: "Connect via access token from the Moomoo/Futu app",
    color: "#FF6B00",
    initial: "M",
  },
  longbridge: {
    name: "Longbridge",
    description: "Connect via OAuth 2.0 authorization",
    color: "#1E90FF",
    initial: "L",
  },
  ibkr: {
    name: "IBKR",
    description: "Connect via API token from IBKR account management",
    color: "#E31837",
    initial: "I",
  },
}

function formatLastSynced(ts: string | null): string {
  if (!ts) return "Never synced"
  try {
    const date = new Date(ts)
    return `Last synced ${date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })}`
  } catch {
    return "Last synced recently"
  }
}

function statusBadge(status: string) {
  if (status === "active") {
    return <Badge variant="success">Active</Badge>
  }
  if (status === "expired" || status === "error") {
    return <Badge variant="error">{status.charAt(0).toUpperCase() + status.slice(1)}</Badge>
  }
  return <Badge variant="warning">{status}</Badge>
}

export function BrokerCard({
  broker,
  connection,
  backendToken,
  onConnect,
  onDisconnect,
}: BrokerCardProps) {
  const meta = BROKER_META[broker]
  const isConnected = Boolean(connection)
  const [drawerOpen, setDrawerOpen] = React.useState(false)
  const [disconnecting, setDisconnecting] = React.useState(false)

  const apiUrl = API_BASE_URL

  function handleConnectClick() {
    if (broker === "longbridge") {
      window.location.href = `${apiUrl}/brokerages/longbridge/oauth/start?token=${encodeURIComponent(backendToken)}`
    } else {
      setDrawerOpen(true)
    }
  }

  async function handleDisconnect() {
    if (!connection) return
    setDisconnecting(true)
    try {
      await onDisconnect(connection.id)
    } finally {
      setDisconnecting(false)
    }
  }

  async function handleDrawerSubmit(credentials: string) {
    await onConnect(broker, credentials)
  }

  return (
    <>
      <Card className="flex flex-col gap-0 overflow-hidden">
        <CardContent className="p-6 flex flex-col gap-4">
          {/* Header row: icon + name + badge */}
          <div className="flex items-start gap-4">
            {/* Colored initial */}
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white text-lg font-bold shadow-sm"
              style={{ backgroundColor: meta.color }}
              aria-hidden="true"
            >
              {meta.initial}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-semibold text-white leading-tight">
                  {meta.name}
                </h3>
                {isConnected && connection ? (
                  statusBadge(connection.status)
                ) : (
                  <Badge
                    variant="default"
                    className="bg-white/10 text-white/40 border-white/10"
                  >
                    Not connected
                  </Badge>
                )}
              </div>
              <p className="mt-1 text-sm text-white/50 leading-snug">
                {meta.description}
              </p>
            </div>
          </div>

          {/* Last synced */}
          {isConnected && connection && (
            <p className="text-xs text-white/30">
              {formatLastSynced(connection.last_synced_at)}
            </p>
          )}

          {/* Action button */}
          <div className="pt-1">
            {isConnected ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDisconnect}
                disabled={disconnecting}
                className={cn("w-full")}
              >
                {disconnecting ? "Disconnecting…" : "Disconnect"}
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={handleConnectClick}
                className="w-full"
              >
                Connect
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Token drawer — only rendered for non-OAuth brokers */}
      {broker !== "longbridge" && (
        <TokenDrawer
          broker={broker}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          onSubmit={handleDrawerSubmit}
        />
      )}
    </>
  )
}
