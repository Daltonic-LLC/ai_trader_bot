import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Define protected routes and their required roles
const PROTECTED_ROUTES = {
  '/dashboard': ['user', 'admin'],
} as const

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // Get raw cookie value
  const bot_user = request.cookies.get('bot_user')?.value || ''

  // Check if the route needs role-based protection
  const requiredRoles =
    PROTECTED_ROUTES[pathname as keyof typeof PROTECTED_ROUTES]

  if (requiredRoles) {
    if (!bot_user) {
      return NextResponse.redirect(new URL('/', request.url))
    }

    try {
      // Parse the cookie to extract role
      const userData = JSON.parse(bot_user)
      const userRole = userData?.role

      // Ensure the user has one of the required roles for the route
      if (!requiredRoles.includes(userRole)) {
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
    } catch (error) {
      console.log(error)
      return NextResponse.redirect(new URL('/', request.url))
    }
  }

  return NextResponse.next()
}

// Export a static config object with explicitly defined paths
export const config = {
  matcher: Object.keys(PROTECTED_ROUTES),
}