import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getToken } from 'next-auth/jwt'

export async function middleware(request: NextRequest) {
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET })
  const isAuthPage = request.nextUrl.pathname.startsWith('/auth/')
  const isApiAuthRoute = request.nextUrl.pathname.startsWith('/api/auth')
  const isPublicPath = request.nextUrl.pathname === '/' || 
                       request.nextUrl.pathname.startsWith('/api/') ||
                       request.nextUrl.pathname.startsWith('/_next/') ||
                       request.nextUrl.pathname.startsWith('/favicon') ||
                       request.nextUrl.pathname === '/upgrade' ||
                       request.nextUrl.pathname.startsWith('/analyzing/') ||
                       request.nextUrl.pathname.startsWith('/blog') ||
                       request.nextUrl.pathname.startsWith('/payment/')

  // Allow API auth routes to pass through
  if (isApiAuthRoute) {
    return NextResponse.next()
  }

  // If user is authenticated and trying to access auth pages, redirect to dashboard
  if (token && isAuthPage) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  // If user is not authenticated and trying to access protected routes
  if (!token && !isAuthPage && !isPublicPath) {
    const callbackUrl = encodeURIComponent(request.nextUrl.pathname + request.nextUrl.search)
    return NextResponse.redirect(new URL(`/auth/signin?callbackUrl=${callbackUrl}`, request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
}