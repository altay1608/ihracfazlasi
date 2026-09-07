import { v2 as cloudinary } from "cloudinary";

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
});

export interface UploadResult {
  url: string;
  publicId: string;
  width: number;
  height: number;
}

// Görsel yükleme (base64 veya URL'den)
export async function uploadImage(
  source: string, // base64 data veya URL
  folder: string = "products"
): Promise<UploadResult> {
  // Check Cloudinary config
  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;

  console.log(`[Cloudinary] Config check - cloud_name: ${cloudName ? "SET" : "MISSING"}, api_key: ${apiKey ? "SET" : "MISSING"}, api_secret: ${apiSecret ? "SET" : "MISSING"}`);

  if (!cloudName || !apiKey || !apiSecret) {
    throw new Error(`Cloudinary config eksik: cloud_name=${!!cloudName}, api_key=${!!apiKey}, api_secret=${!!apiSecret}`);
  }

  try {
    console.log(`[Cloudinary] Uploading from: ${source.substring(0, 50)}...`);

    const result = await cloudinary.uploader.upload(source, {
      folder: `ihrac-fazlasi/${folder}`,
      transformation: [
        { width: 1200, height: 1200, crop: "limit" },
        { quality: "auto:good" },
        { format: "webp" },
      ],
    });

    console.log(`[Cloudinary] Upload success: ${result.secure_url}`);

    return {
      url: result.secure_url,
      publicId: result.public_id,
      width: result.width,
      height: result.height,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error("[Cloudinary] Upload error:", errorMsg, error);
    throw new Error(`Görsel yükleme başarısız: ${errorMsg}`);
  }
}

// URL'den görsel yükleme
export async function uploadImageFromUrl(
  imageUrl: string,
  folder: string = "products"
): Promise<UploadResult> {
  return uploadImage(imageUrl, folder);
}

// Video yükleme sonucu
export interface VideoUploadResult {
  url: string;
  publicId: string;
  width: number;
  height: number;
  duration: number;
  thumbnailUrl: string;
}

// URL'den video yükleme
export async function uploadVideoFromUrl(
  videoUrl: string,
  folder: string = "products"
): Promise<VideoUploadResult> {
  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;

  console.log(`[Cloudinary Video] Config check - cloud_name: ${cloudName ? "SET" : "MISSING"}`);

  if (!cloudName || !apiKey || !apiSecret) {
    throw new Error(`Cloudinary config eksik`);
  }

  try {
    console.log(`[Cloudinary Video] Uploading from: ${videoUrl.substring(0, 50)}...`);

    const result = await cloudinary.uploader.upload(videoUrl, {
      folder: `ihrac-fazlasi/${folder}`,
      resource_type: "video",
      transformation: [
        { quality: "auto:good" },
        { format: "mp4" },
      ],
    });

    console.log(`[Cloudinary Video] Upload success: ${result.secure_url}`);

    // Generate thumbnail URL from video
    const thumbnailUrl = result.secure_url
      .replace("/video/upload/", "/video/upload/so_0,w_800,h_800,c_limit,f_jpg/")
      .replace(/\.[^/.]+$/, ".jpg");

    return {
      url: result.secure_url,
      publicId: result.public_id,
      width: result.width,
      height: result.height,
      duration: result.duration || 0,
      thumbnailUrl,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error("[Cloudinary Video] Upload error:", errorMsg, error);
    throw new Error(`Video yükleme başarısız: ${errorMsg}`);
  }
}

// Görsel silme
export async function deleteImage(publicId: string): Promise<boolean> {
  try {
    await cloudinary.uploader.destroy(publicId);
    return true;
  } catch (error) {
    console.error("Cloudinary delete error:", error);
    return false;
  }
}

// Optimize edilmiş görsel URL'i oluşturma
export function getOptimizedUrl(
  url: string,
  options: {
    width?: number;
    height?: number;
    quality?: string;
  } = {}
): string {
  const { width = 800, height, quality = "auto:good" } = options;

  // Cloudinary URL'i değilse olduğu gibi döndür
  if (!url.includes("cloudinary.com")) {
    return url;
  }

  // URL'den transformation ekle
  const parts = url.split("/upload/");
  if (parts.length !== 2) return url;

  const transformations = [`q_${quality}`, `w_${width}`];
  if (height) transformations.push(`h_${height}`);
  transformations.push("c_limit", "f_auto");

  return `${parts[0]}/upload/${transformations.join(",")}/${parts[1]}`;
}

export default cloudinary;
