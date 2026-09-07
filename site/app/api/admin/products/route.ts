import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

async function checkAuth(request: NextRequest) {
  const cookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  return validateAdminSession(cookie || '');
}

export async function GET(request: NextRequest) {
  if (!(await checkAuth(request))) {
    return NextResponse.json({ success: false }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const search = searchParams.get('search') || '';
  const categoryId = searchParams.get('categoryId');
  const page = parseInt(searchParams.get('page') || '1');
  const limit = 20;
  const skip = (page - 1) * limit;

  const where: Record<string, unknown> = {};
  if (search) {
    where.OR = [{ name: { contains: search } }, { sku: { contains: search } }];
  }
  if (categoryId) {
    where.categoryId = parseInt(categoryId);
  }

  const [products, total] = await Promise.all([
    prisma.product.findMany({
      where,
      include: {
        category: { select: { id: true, name: true } },
        variants: { select: { id: true, size: true, color: true, stock: true } },
        images: { where: { isPrimary: true }, take: 1 },
      },
      orderBy: { createdAt: 'desc' },
      skip,
      take: limit,
    }),
    prisma.product.count({ where }),
  ]);

  return NextResponse.json({
    success: true,
    data: products,
    pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
  });
}

export async function POST(request: NextRequest) {
  if (!(await checkAuth(request))) {
    return NextResponse.json({ success: false }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { name, sku, description, categoryId, price, costPrice, isActive, imageUrl } = body;

    if (!name || !sku || price === undefined) {
      return NextResponse.json(
        { success: false, message: 'Ad, SKU ve fiyat zorunlu' },
        { status: 400 }
      );
    }

    const product = await prisma.product.create({
      data: {
        name: name.trim(),
        sku: sku.trim().toUpperCase(),
        description: description?.trim() || null,
        categoryId: categoryId ? parseInt(categoryId) : null,
        price: parseFloat(price),
        costPrice: costPrice ? parseFloat(costPrice) : null,
        isActive: isActive !== false,
        ...(imageUrl ? {
          images: {
            create: { imageUrl, isPrimary: true, sortOrder: 0 },
          },
        } : {}),
      },
      include: { images: true },
    });

    return NextResponse.json({ success: true, data: product }, { status: 201 });
  } catch (error: unknown) {
    if (
      error &&
      typeof error === 'object' &&
      'code' in error &&
      (error as { code: string }).code === 'P2002'
    ) {
      return NextResponse.json(
        { success: false, message: 'Bu SKU zaten kullanılıyor' },
        { status: 409 }
      );
    }
    console.error('Product create error:', error);
    return NextResponse.json({ success: false, message: 'Ürün eklenemedi' }, { status: 500 });
  }
}
