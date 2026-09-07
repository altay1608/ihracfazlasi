import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

async function checkAuth(request: NextRequest) {
  const cookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  return validateAdminSession(cookie || '');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  try {
    const { id } = await params;
    const { name, slug, isActive } = await request.json();

    const category = await prisma.category.update({
      where: { id: parseInt(id) },
      data: {
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
        isActive: isActive !== false,
      },
    });

    return NextResponse.json({ success: true, data: category });
  } catch (error) {
    console.error('Category update error:', error);
    return NextResponse.json({ success: false, message: 'Güncellenemedi' }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!(await checkAuth(request))) return NextResponse.json({ success: false }, { status: 401 });

  try {
    const { id } = await params;
    await prisma.category.delete({ where: { id: parseInt(id) } });
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Category delete error:', error);
    return NextResponse.json(
      { success: false, message: 'Silinemedi. Bağlı ürünler olabilir.' },
      { status: 400 }
    );
  }
}
