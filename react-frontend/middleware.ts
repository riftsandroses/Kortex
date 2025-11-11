import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// ✅ This must be a named export exactly called “middleware”
export function middleware(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value

  // Redirect if user is not logged in
  if (
    !token &&
    (request.nextUrl.pathname.startsWith("/dashboard") ||
      request.nextUrl.pathname.startsWith("/kobra"))
  ) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  return NextResponse.next()
}

// ✅ Ensure config is exported separately
export const config = {
  matcher: ["/dashboard/:path*", "/kobra/:path*"],
}
