import { NextRequest, NextResponse } from 'next/server';
import { login, ADMIN_COOKIE_NAME, COOKIE_OPTIONS } from '@/lib/admin-auth';

export async function POST(request: NextRequest) {
  try {
    const { password } = await request.json();

    if (!password) {
      return NextResponse.json({ success: false, message: 'Şifre gerekli' }, { status: 400 });
    }

    const result = await login(password);

    if (!result.success) {
      return NextResponse.json({ success: false, message: 'Yanlış şifre' }, { status: 401 });
    }

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
