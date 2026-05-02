"use client"

import * as React from "react"
import { Drawer } from "@/components/ui/drawer"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export interface TokenDrawerProps {
  broker: "moomoo" | "ibkr"
  open: boolean
  onClose: () => void
  onSubmit: (credentials: string) => Promise<void>
}

const DRAWER_TITLES: Record<TokenDrawerProps["broker"], string> = {
  moomoo: "Connect Moomoo",
  ibkr: "Connect IBKR",
}

export function TokenDrawer({ broker, open, onClose, onSubmit }: TokenDrawerProps) {
  const [accessToken, setAccessToken] = React.useState("")
  const [accountId, setAccountId] = React.useState("")
  const [apiToken, setApiToken] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Reset fields when drawer opens/closes
  React.useEffect(() => {
    if (!open) {
      setAccessToken("")
      setAccountId("")
      setApiToken("")
      setError(null)
    }
  }, [open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    let credentials: string
    if (broker === "moomoo") {
      if (!accessToken.trim() || !accountId.trim()) {
        setError("Both fields are required.")
        return
      }
      credentials = JSON.stringify({
        access_token: accessToken.trim(),
        account_id: accountId.trim(),
      })
    } else {
      if (!apiToken.trim()) {
        setError("API token is required.")
        return
      }
      credentials = JSON.stringify({ api_token: apiToken.trim() })
    }

    setLoading(true)
    try {
      await onSubmit(credentials)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Drawer open={open} onClose={onClose} title={DRAWER_TITLES[broker]}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {broker === "moomoo" && (
          <>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="access-token">Access Token</Label>
              <Input
                id="access-token"
                type="password"
                placeholder="Paste your Moomoo access token"
                value={accessToken}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAccessToken(e.target.value)}
                disabled={loading}
                autoComplete="off"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="account-id">Account ID</Label>
              <Input
                id="account-id"
                type="text"
                placeholder="Your Moomoo account ID"
                value={accountId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAccountId(e.target.value)}
                disabled={loading}
                autoComplete="off"
              />
            </div>
          </>
        )}

        {broker === "ibkr" && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="api-token">API Token</Label>
            <Input
              id="api-token"
              type="password"
              placeholder="Paste your IBKR API token"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              disabled={loading}
              autoComplete="off"
            />
          </div>
        )}

        {error && (
          <p className="text-sm text-red-400">{error}</p>
        )}

        <div className="flex gap-3 pt-1">
          <Button
            type="submit"
            disabled={loading}
            className="flex-1"
          >
            {loading ? "Connecting…" : "Connect"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </Button>
        </div>
      </form>
    </Drawer>
  )
}
