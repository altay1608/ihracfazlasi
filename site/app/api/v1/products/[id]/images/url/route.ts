import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { uploadImageFromUrl } from "@/lib/cloudinary";
import { z } from "zod";

interface RouteContext {
  params: Promise<{ id: string }>;
}

const uploadFromUrlSchema = z.object({
  // Support both camelCase and snake_case - use string() instead of url() for Telegram URLs
  image_url: z.string().min(1, "URL gerekli").optional(),
  imageUrl: z.string().min(1, "URL gerekli").optional(),
  is_primary: z.boolean().optional(),
  isPrimary: z.boolean().optional(),
}).refine(data => data.image_url || data.imageUrl, {
  message: "image_url veya imageUrl gerekli",
});

// POST /api/v1/products/[id]/images/url - URL'den görsel ekle
export async function POST(request: NextRequest, context: RouteContext) {
  const auth = await validateApiKey(request);
  if (!auth.success) return auth.error;

  try {
    const { id } = await context.params;
    const productId = parseInt(id);

    if (isNaN(productId)) {
      return errorResponse("INVALID_ID", "Geçersiz ürün ID", undefined, 400);
    }

    // Check if product exists
    const product = await prisma.product.findUnique({
      where: { id: productId },
      include: { images: true },
    });

    if (!product) {
      return errorResponse("PRODUCT_NOT_FOUND", "Ürün bulunamadı", undefined, 404);
    }

    const body = await request.json();
    console.log(`[Image Upload] Request body:`, JSON.stringify(body));

    const validation = uploadFromUrlSchema.safeParse(body);

    if (!validation.success) {
      console.error(`[Image Upload] Validation error:`, validation.error.errors);
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => `${e.path.join(".")}: ${e.message}`).join(", ")
      );
    }

    // Support both naming conventions
    const imageUrl = validation.data.image_url || validation.data.imageUrl!;
    const isPrimary = validation.data.is_primary ?? validation.data.isPrimary ?? false;

    console.log(`[Image Upload] Product ID: ${productId}, URL: ${imageUrl.substring(0, 50)}...`);

    // Upload from URL to Cloudinary
    const uploadResult = await uploadImageFromUrl(imageUrl, "products");
    console.log(`[Image Upload] Cloudinary result:`, uploadResult.url);

    // If setting as primary, unset other primaries
    if (isPrimary) {
      await prisma.productImage.updateMany({
        where: { productId },
        data: { isPrimary: false },
      });
    }

    // Save to database
    const image = await prisma.productImage.create({
      data: {
        productId,
        imageUrl: uploadResult.url,
        isPrimary: isPrimary || product.images.length === 0,
        sortOrder: product.images.length,
      },
    });
    console.log(`[Image Upload] Saved to DB, image ID: ${image.id}`);

    return successResponse(
      {
        id: image.id,
        url: image.imageUrl,
        isPrimary: image.isPrimary,
      },
      201
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("[Image Upload] Error:", errorMessage, error);
    return errorResponse(
      "UPLOAD_ERROR",
      "URL'den görsel yüklenemedi",
      errorMessage,
      500
    );
  }
}
