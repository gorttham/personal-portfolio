import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"
import { ConnectPageClient } from "@/components/connect/ConnectPageClient"

export default async function ConnectPage() {
  const session = await auth()
  if (!session) redirect("/")
  return <ConnectPageClient backendToken={session.backendToken} />
}
