"use client"
import { signInWithProvider } from "@/app/auth/actions"
import { Button } from "@/components/ui/button"

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-2xl border border-border-subtle bg-surface">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-semibold text-white">Welcome back</h1>
          <p className="text-sm text-white/50">Sign in to your portfolio</p>
        </div>
        <div className="space-y-3">
          <form action={signInWithProvider.bind(null, "google")}>
            <Button type="submit" className="w-full" variant="outline">
              Continue with Google
            </Button>
          </form>
          <form action={signInWithProvider.bind(null, "github")}>
            <Button type="submit" className="w-full" variant="outline">
              Continue with GitHub
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
