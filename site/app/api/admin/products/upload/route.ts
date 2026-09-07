import { NextRequest, NextResponse } from 'next/server';
import { validateAdminSession, ADMIN_COOKIE_NAME } from '@/lib/admin-auth';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

export async function POST(request: NextRequest) {
  const cookie = request.cookies.get(ADMIN_COOKIE_NAME)?.value;
  if (!(await validateAdminSession(cookie || ''))) {
    return NextResponse.json({ success: false }, { status: 401 });
  }

  try {
    const formData = await request.formData();
    const file = formData.get('image') as File | null;

    if (!file || file.size === 0) {
      return NextResponse.json({ success: false, message: 'Görsel seçilmedi' }, { status: 400 });
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      return NextResponse.json(
        { success: false, message: 'Yalnızca JPG, PNG, WebP veya GIF yüklenebilir' },
        { status: 400 }
      );
    }
    if (file.size > MAX_SIZE) {
      return NextResponse.json(
        { success: false, message: 'Görsel 5MB üzerinde olamaz' },
        { status: 400 }
      );
    }

    // Cloudinary varsa ona yükle, yoksa local'e kaydet
    const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
    const apiKey = process.env.CLOUDINARY_API_KEY;
    const apiSecret = process.env.CLOUDINARY_API_SECRET;

    if (cloudName && apiKey && apiSecret &&
        cloudName !== 'your-cloud-name' && apiKey !== 'your-api-key') {
      // --- Cloudinary yükleme ---
      const bytes = await file.arrayBuffer();
      const base64 = Buffer.from(bytes).toString('base64');
      const dataUri = `data:${file.type};base64,${base64}`;

      const { uploadImage } = await import('@/lib/cloudinary');
      const result = await uploadImage(dataUri, 'admin-products');
      return NextResponse.json({ success: true, url: result.url });
    } else {
      // --- Local fallback (geliştirme ortamı) ---
      const { writeFile, mkdir } = await import('fs/promises');
      const { join, extname } = await import('path');

      const ext = extname(file.name) || '.jpg';
      const safeBase = file.name
        .replace(/\.[^.]+$/, '')
        .replace(/[^a-zA-Z0-9]/g, '_')
        .substring(0, 40);
      const filename = `${Date.now()}-${safeBase}${ext}`;
      const uploadDir = join(process.cwd(), 'public', 'uploads', 'products');
      await mkdir(uploadDir, { recursive: true });
      const bytes = await file.arrayBuffer();
      await writeFile(join(uploadDir, filename), Buffer.from(bytes));
      return NextResponse.json({ success: true, url: `/uploads/products/${filename}` });
    }
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json({ success: false, message: 'Yükleme başarısız' }, { status: 500 });
  }
}
