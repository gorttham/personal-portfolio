"use server"
import { signIn } from "@/lib/auth"

export async function signInWithProvider(provider: string) {
  await signIn(provider, { redirectTo: "/dashboard" })
}
