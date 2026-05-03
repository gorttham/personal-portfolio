"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { BotMessageSquare } from "lucide-react"
import { ChatPanel } from "@/components/dashboard/ChatPanel"

export function DashboardChatToggle() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setChatOpen(true)}
        className="flex items-center gap-2"
      >
        <BotMessageSquare className="h-4 w-4" />
        <span>AI Chat</span>
      </Button>
      <ChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />
    </>
  )
}
