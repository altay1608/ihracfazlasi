import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

async function checkAuth(request: NextRequest) {
  const cookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  return validateAdminSession(cookie || '');
}

export async function GET(request: NextRequest) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  const categories = await prisma.category.findMany({
    orderBy: { name: 'asc' },
    include: { _count: { select: { products: true } } },
  });

  return NextResponse.json({ success: true, data: categories });
}

export async function POST(request: NextRequest) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  try {
    const { name, slug, parentId, isActive } = await request.json();

    if (!name || !slug) {
      return NextResponse.json(
        { success: false, message: 'Ad ve slug zorunlu' },
        { status: 400 }
      );
    }

    const category = await prisma.category.create({
      data: {
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
        parentId: parentId || null,
        isActive: isActive !== false,
      },
    });

    return NextResponse.json({ success: true, data: category }, { status: 201 });
  } catch (error: unknown) {
    if (
      error &&
      typeof error === 'object' &&
      'code' in error &&
      (error as { code: string }).code === 'P2002'
    ) {
      return NextResponse.json(
        { success: false, message: 'Bu slug zaten kullanılıyor' },
        { status: 409 }
      );
    }
    return NextResponse.json({ success: false, message: 'Kategori eklenemedi' }, { status: 500 });
  }
}
