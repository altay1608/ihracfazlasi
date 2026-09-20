import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { validateAdminSession } from "@/lib/admin-auth";

export async function middleware(request: NextRequest) {
  const url = request.nextUrl;
  const { pathname, search } = url;
  const fullUrl = request.url;

  // Admin route protection
  if (pathname.startsWith('/admin') && !pathname.startsWith('/admin/login')) {
    const adminSession = request.cookies.get('admin-session')?.value;
    if (!adminSession) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }

    if (!(await validateAdminSession(adminSession))) {
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
