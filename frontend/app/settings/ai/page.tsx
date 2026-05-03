"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { CheckCircle, XCircle, Loader2 } from "lucide-react"

const MODELS: Record<string, string[]> = {
  anthropic: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4o", "gpt-4o-mini"],
}

type Status = "idle" | "saving" | "testing" | "saved" | "error"

export default function AISettingsPage() {
  const { data: session } = useSession()
  const router = useRouter()

  const [provider, setProvider] = useState<"anthropic" | "openai">("anthropic")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState(MODELS.anthropic[0])
  const [isConfigured, setIsConfigured] = useState(false)
  const [status, setStatus] = useState<Status>("idle")
  const [message, setMessage] = useState("")
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

  useEffect(() => {
    if (!session?.backendToken) return
    fetch(`${backendUrl}/ai/settings`, {
      headers: { Authorization: `Bearer ${session.backendToken}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.configured) {
          setIsConfigured(true)
          setProvider(data.provider)
          setModel(data.model)
        }
      })
      .catch(() => {})
  }, [session, backendUrl])

  const handleProviderChange = (val: "anthropic" | "openai") => {
    setProvider(val)
    setModel(MODELS[val][0])
    setTestResult(null)
  }

  const handleSave = async () => {
    if (!apiKey && !isConfigured) {
      setMessage("Please enter an API key.")
      setStatus("error")
      return
    }
    setStatus("saving")
    setMessage("")
    try {
      const res = await fetch(`${backendUrl}/ai/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.backendToken}`,
        },
        body: JSON.stringify({ provider, api_key: apiKey || "__KEEP__", model }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setIsConfigured(data.configured)
      setApiKey("")
      setStatus("saved")
      setMessage("Settings saved successfully.")
    } catch (err: unknown) {
      setStatus("error")
      setMessage(err instanceof Error ? err.message : "Failed to save settings.")
    }
  }

  const handleTest = async () => {
    setStatus("testing")
    setTestResult(null)
    try {
      const res = await fetch(`${backendUrl}/ai/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.backendToken}` },
      })
      const data = await res.json()
      setTestResult(data)
    } catch {
      setTestResult({ success: false, error: "Network error" })
    } finally {
      setStatus("idle")
    }
  }

  return (
    <div className="max-w-lg mx-auto py-10 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Settings</h1>
        <p className="text-white/50 mt-1 text-sm">
          Connect your own Anthropic or OpenAI API key to enable the AI chat panel.
        </p>
      </div>

      <div className="space-y-2">
        <Label className="text-white">Provider</Label>
        <RadioGroup
          value={provider}
          onValueChange={(v) => handleProviderChange(v as "anthropic" | "openai")}
          className="flex gap-6"
        >
          <div className="flex items-center gap-2">
            <RadioGroupItem value="anthropic" id="prov-anthropic" />
            <Label htmlFor="prov-anthropic" className="text-white cursor-pointer">Anthropic</Label>
          </div>
          <div className="flex items-center gap-2">
            <RadioGroupItem value="openai" id="prov-openai" />
            <Label htmlFor="prov-openai" className="text-white cursor-pointer">OpenAI</Label>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label htmlFor="model-select" className="text-white">Model</Label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger id="model-select" className="w-full">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {MODELS[provider].map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="api-key" className="text-white">
          API Key{" "}
          {isConfigured && (
            <span className="text-xs text-white/40 ml-1">(leave blank to keep existing key)</span>
          )}
        </Label>
        <Input
          id="api-key"
          type="password"
          placeholder={isConfigured ? "••••••••••••••••" : "sk-ant-... or sk-..."}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          autoComplete="off"
        />
      </div>

      {status === "saved" && (
        <Alert className="border-emerald-500/50 bg-emerald-500/10 text-emerald-400">
          <CheckCircle className="h-4 w-4 shrink-0" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}
      {status === "error" && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4 shrink-0" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}
      {testResult && (
        <Alert
          variant={testResult.success ? "default" : "destructive"}
          className={testResult.success ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400" : ""}
        >
          {testResult.success ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <AlertDescription>
            {testResult.success
              ? "Connection successful — API key is valid."
              : `Connection failed: ${testResult.error}`}
          </AlertDescription>
        </Alert>
      )}

      <div className="flex gap-3">
        <Button onClick={handleSave} disabled={status === "saving" || status === "testing"}>
          {status === "saving" ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving…</>
          ) : (
            "Save"
          )}
        </Button>
        <Button
          variant="outline"
          onClick={handleTest}
          disabled={!isConfigured || status === "saving" || status === "testing"}
        >
          {status === "testing" ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Testing…</>
          ) : (
            "Test connection"
          )}
        </Button>
        <Button variant="ghost" onClick={() => router.back()}>Back</Button>
      </div>
    </div>
  )
}
