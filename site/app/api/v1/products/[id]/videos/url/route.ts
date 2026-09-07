import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { validateApiKey, successResponse, errorResponse } from "@/lib/api-auth";
import { uploadVideoFromUrl } from "@/lib/cloudinary";
import { z } from "zod";

interface RouteContext {
  params: Promise<{ id: string }>;
}

const uploadVideoSchema = z.object({
  video_url: z.string().min(1, "URL gerekli").optional(),
  videoUrl: z.string().min(1, "URL gerekli").optional(),
  is_primary: z.boolean().optional(),
  isPrimary: z.boolean().optional(),
}).refine(data => data.video_url || data.videoUrl, {
  message: "video_url veya videoUrl gerekli",
});

// POST /api/v1/products/[id]/videos/url - URL'den video ekle
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
    console.log(`[Video Upload] Request body:`, JSON.stringify(body));

    const validation = uploadVideoSchema.safeParse(body);

    if (!validation.success) {
      console.error(`[Video Upload] Validation error:`, validation.error.errors);
      return errorResponse(
        "VALIDATION_ERROR",
        "Geçersiz veri",
        validation.error.errors.map((e) => `${e.path.join(".")}: ${e.message}`).join(", ")
      );
    }

    // Support both naming conventions
    const videoUrl = validation.data.video_url || validation.data.videoUrl!;
    const isPrimary = validation.data.is_primary ?? validation.data.isPrimary ?? false;

    console.log(`[Video Upload] Product ID: ${productId}, URL: ${videoUrl.substring(0, 50)}...`);

    // Upload video to Cloudinary
    const uploadResult = await uploadVideoFromUrl(videoUrl, "products/videos");
    console.log(`[Video Upload] Cloudinary result:`, uploadResult.url);

    // If setting as primary, unset other primaries
    if (isPrimary) {
      await prisma.productImage.updateMany({
        where: { productId },
        data: { isPrimary: false },
      });
    }

    // Save video as image (with video URL) - thumbnail for display
    const image = await prisma.productImage.create({
      data: {
        productId,
        imageUrl: uploadResult.url, // Video URL
        isPrimary: isPrimary || product.images.length === 0,
        sortOrder: product.images.length,
      },
    });

    // Also save thumbnail as separate image if this is primary
    if (isPrimary || product.images.length === 0) {
      await prisma.productImage.create({
        data: {
          productId,
          imageUrl: uploadResult.thumbnailUrl,
          isPrimary: false,
          sortOrder: product.images.length + 1,
        },
      });
    }

    console.log(`[Video Upload] Saved to DB, image ID: ${image.id}`);

    return successResponse(
      {
        id: image.id,
        url: uploadResult.url,
        thumbnailUrl: uploadResult.thumbnailUrl,
        duration: uploadResult.duration,
        isPrimary: image.isPrimary,
        type: "video",
      },
      201
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("[Video Upload] Error:", errorMessage, error);
    return errorResponse(
      "UPLOAD_ERROR",
      "URL'den video yüklenemedi",
      errorMessage,
      500
    );
  }
}
