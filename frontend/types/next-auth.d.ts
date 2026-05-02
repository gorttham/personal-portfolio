import "next-auth"

declare module "next-auth" {
  interface Session {
    backendToken: string
    user: {
      name: string
      email: string
      image: string
    }
  }
}
