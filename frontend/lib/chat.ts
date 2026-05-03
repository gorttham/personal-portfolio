export type ChatMessage = {
  role: "user" | "assistant"
  content: string
}

export function streamChatMessage({
  message,
  backendUrl,
  backendToken,
  onToken,
  onDone,
  onError,
}: {
  message: string
  backendUrl: string
  backendToken: string
  onToken: (token: string) => void
  onDone: () => void
  onError: (err: string) => void
}): () => void {
  const controller = new AbortController()

  ;(async () => {
    let response: Response
    try {
      response = await fetch(`${backendUrl}/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${backendToken}`,
        },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      })
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError("Failed to connect to AI service.")
      }
      return
    }

    if (!response.ok) {
      onError(`AI service error: ${response.status}`)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError("No response body from AI service.")
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const parsed = JSON.parse(raw) as { token?: string; done?: boolean }
            if (parsed.done) {
              onDone()
              return
            }
            if (typeof parsed.token === "string") {
              onToken(parsed.token)
            }
          } catch {
            // malformed SSE line — skip
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError("Stream interrupted.")
      }
    } finally {
      reader.releaseLock()
    }

    onDone()
  })()

  return () => controller.abort()
}
