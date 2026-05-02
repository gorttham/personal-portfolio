import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import { encode } from "next-auth/jwt"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.email = user.email
        token.name = user.name
        token.picture = user.image
      }
      return token
    },
    async session({ session, token }) {
      // Re-encode the JWT so the backend can verify it
      const backendToken = await encode({
        token,
        secret: process.env.NEXTAUTH_SECRET!,
      })
      return {
        ...session,
        backendToken,
        user: {
          ...session.user,
          email: token.email as string,
          name: token.name as string,
          image: token.picture as string,
        },
      }
    },
  },
  pages: {
    signIn: "/auth/signin",
  },
})
