import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

async function computeAdminToken(password: string): Promise<string> {
  const salt = process.env.ADMIN_SECRET || 'ihrac-admin-salt-2026';
  const data = new TextEncoder().encode(password + salt);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function middleware(request: NextRequest) {
  const url = request.nextUrl;
  const { pathname, search } = url;
  const fullUrl = request.url;

  // Admin route protection
  if (pathname.startsWith('/admin') && !pathname.startsWith('/admin/login')) {
    const adminSession = request.cookies.get('admin-session')?.value;
    const adminPassword = process.env.ADMIN_PASSWORD;

    if (!adminSession || !adminPassword) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }

    const expectedToken = await computeAdminToken(adminPassword);
    if (adminSession !== expectedToken) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }

    return NextResponse.next();
  }

  // Eski URL formatlarini yakala ve 301 redirect yap
  const productMatch = fullUrl.match(/\?product\/(\d+)/);
  if (productMatch) {
    return NextResponse.redirect(new URL("/urunler", request.url), { status: 301 });
  }

  const categoryMatch = fullUrl.match(/\?category\/([a-z0-9-]+)/i);
  if (categoryMatch) {
    const slug = categoryMatch[1].toLowerCase();
    return NextResponse.redirect(new URL(`/kategori/${slug}`, request.url), { status: 301 });
  }

  // /panel rotasında trailing slash redirect yapmıyoruz (Flask proxy)
  if (!pathname.startsWith('/panel') && pathname !== "/" && pathname.endsWith("/")) {
    const newUrl = new URL(pathname.slice(0, -1) + search, request.url);
    return NextResponse.redirect(newUrl, { status: 301 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|logo.png|og-image.jpg).*)",
  ],
};
