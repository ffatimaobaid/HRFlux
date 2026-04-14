import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Protect all /admin routes
  if (pathname.startsWith('/admin')) {
    const role = request.cookies.get('hrflux_role')?.value;
    
    // If not admin, redirect to dashboard or login
    if (role !== 'admin') {
      const url = request.nextUrl.clone();
      
      // If no role at all, they might not be logged in
      if (!role) {
        url.pathname = '/login';
      } else {
        url.pathname = '/dashboard';
      }
      
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

// See "Matching Paths" below to learn more
export const config = {
  matcher: ['/admin', '/admin/:path*'],
};
