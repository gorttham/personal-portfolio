"use client"

import { useEffect, useRef, useState } from "react"
import { useSession } from "next-auth/react"
import Link from "next/link"
import { X, Send, Loader2, BotMessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { streamChatMessage, type ChatMessage } from "@/lib/chat"

interface AISummary {
  configured: boolean
  provider?: string
  model?: string
}

interface ChatPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function ChatPanel({ isOpen, onClose }: ChatPanelProps) {
  const { data: session } = useSession()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [aiSummary, setAISummary] = useState<AISummary | null>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

  useEffect(() => {
    if (!isOpen || !session?.backendToken) return
    fetch(`${backendUrl}/ai/settings`, {
      headers: { Authorization: `Bearer ${session.backendToken}` },
    })
      .then((r) => r.json())
      .then((data: AISummary) => setAISummary(data))
      .catch(() => setAISummary({ configured: false }))
  }, [isOpen, session, backendUrl])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isStreaming || !session?.backendToken) return

    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: text }])
    setMessages((prev) => [...prev, { role: "assistant", content: "" }])
    setIsStreaming(true)

    const abort = streamChatMessage({
      message: text,
      backendUrl,
      backendToken: session.backendToken as string,
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: last.content + token }
          }
          return updated
        })
      },
      onDone: () => {
        setIsStreaming(false)
        abortRef.current = null
      },
      onError: (err) => {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: "assistant", content: `Error: ${err}` }
          return updated
        })
        setIsStreaming(false)
        abortRef.current = null
      },
    })

    abortRef.current = abort
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClose = () => {
    abortRef.current?.()
    onClose()
  }

  const isConfigured = aiSummary?.configured ?? false

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={handleClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed top-0 right-0 h-full w-80 md:w-96 bg-[#0a0a0f] border-l border-white/10 shadow-2xl z-40",
          "flex flex-col transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
        aria-label="AI Chat Panel"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <BotMessageSquare className="h-5 w-5 text-white/40" />
            <div>
              <p className="text-sm font-semibold text-white leading-none">
                {aiSummary?.provider
                  ? aiSummary.provider.charAt(0).toUpperCase() + aiSummary.provider.slice(1)
                  : "AI Assistant"}
              </p>
              {aiSummary?.model && (
                <p className="text-xs text-white/40 mt-0.5">{aiSummary.model}</p>
              )}
            </div>
            <span
              className={cn(
                "ml-1 inline-block h-2 w-2 rounded-full",
                isConfigured ? "bg-emerald-500" : "bg-red-500",
              )}
              title={isConfigured ? "Configured" : "Not configured"}
            />
          </div>
          <Button variant="ghost" size="icon" onClick={handleClose} aria-label="Close chat panel">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {!isConfigured && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <BotMessageSquare className="h-10 w-10 text-white/20" />
            <p className="text-sm text-white/50">
              No AI provider configured. Add your API key to start chatting about your portfolio.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link href="/settings/ai">Configure AI in Settings</Link>
            </Button>
          </div>
        )}

        {isConfigured && (
          <>
            <ScrollArea className="flex-1 px-4 py-3">
              {messages.length === 0 && (
                <p className="text-sm text-white/40 text-center mt-8">
                  Ask anything about your portfolio…
                </p>
              )}
              <div className="flex flex-col gap-3">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={cn(
                      "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                      msg.role === "user"
                        ? "self-end bg-[#6366f1] text-white"
                        : "self-start bg-white/8 text-white",
                    )}
                  >
                    {msg.content}
                    {msg.role === "assistant" && msg.content === "" && isStreaming && (
                      <Loader2 className="h-3 w-3 animate-spin inline-block ml-1" />
                    )}
                  </div>
                ))}
              </div>
              <div ref={bottomRef} />
            </ScrollArea>

            <div className="flex items-center gap-2 px-4 py-3 border-t border-white/10 shrink-0">
              <Input
                placeholder="Ask about your portfolio…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
                className="flex-1"
                aria-label="Chat input"
              />
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                aria-label="Send message"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </>
        )}
      </aside>
    </>
  )
}
