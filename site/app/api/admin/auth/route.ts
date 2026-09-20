import { NextRequest, NextResponse } from 'next/server';
import { login, ADMIN_COOKIE_NAME, COOKIE_OPTIONS } from '@/lib/admin-auth';

const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const MAX_LOGIN_ATTEMPTS = 5;
const attempts = new Map<string, { count: number; resetAt: number }>();

function clientKey(request: NextRequest): string {
  return request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || request.headers.get('x-real-ip')
    || 'unknown';
}

export async function POST(request: NextRequest) {
  try {
    const key = clientKey(request);
    const now = Date.now();
    const current = attempts.get(key);
    if (current && current.resetAt > now && current.count >= MAX_LOGIN_ATTEMPTS) {
      const retryAfter = Math.max(1, Math.ceil((current.resetAt - now) / 1000));
      return NextResponse.json(
        { success: false, message: 'Çok fazla başarısız deneme. Lütfen daha sonra tekrar deneyin.' },
        { status: 429, headers: { 'Retry-After': String(retryAfter) } }
      );
    }
    if (current && current.resetAt <= now) attempts.delete(key);

    const { password } = await request.json();

    if (!password) {
      return NextResponse.json({ success: false, message: 'Şifre gerekli' }, { status: 400 });
    }

    const result = await login(password);

    if (!result.success) {
      const active = attempts.get(key);
      attempts.set(key, {
        count: (active?.count || 0) + 1,
        resetAt: active?.resetAt && active.resetAt > now ? active.resetAt : now + LOGIN_WINDOW_MS,
      });
      return NextResponse.json({ success: false, message: 'Yanlış şifre' }, { status: 401 });
    }

    attempts.delete(key);
    const response = NextResponse.json({ success: true });
    response.cookies.set(ADMIN_COOKIE_NAME, result.token, COOKIE_OPTIONS);
    return response;
  } catch {
    return NextResponse.json({ success: false, message: 'Sunucu hatası' }, { status: 500 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ success: true });
  response.cookies.delete(ADMIN_COOKIE_NAME);
  return response;
}
