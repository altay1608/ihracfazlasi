"use client";

import { useState, useCallback } from "react";
import { formatPrice, slugify } from "@/lib/utils";

interface ShareButtonsProps {
  product: {
    name: string;
    price: number;
    sku: string;
    primaryImage?: string | null;
  };
  productUrl: string;
}

export default function ShareButtons({ product, productUrl }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);
  const [generatingStory, setGeneratingStory] = useState(false);
  const [showQR, setShowQR] = useState(false);

  const fullUrl = typeof window !== "undefined"
    ? `${window.location.origin}${productUrl}`
    : productUrl;

  const shareText = `${product.name} - ${formatPrice(product.price)} | İhraç Fazlası Giyim`;

  // Check if Web Share API is available (mostly mobile)
  const canShare = typeof navigator !== "undefined" && navigator.share;

  // Copy link to clipboard
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = fullUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [fullUrl]);

  // Share using Web Share API (mobile)
  const handleShare = useCallback(async () => {
    if (canShare) {
      try {
        await navigator.share({
          title: product.name,
          text: shareText,
          url: fullUrl,
        });
      } catch (err) {
        // User cancelled or error - fallback to copy
        if ((err as Error).name !== "AbortError") {
          copyToClipboard();
        }
      }
    } else {
      copyToClipboard();
    }
  }, [canShare, product.name, shareText, fullUrl, copyToClipboard]);

  // Generate Instagram Story image (1080x1920)
  const generateStoryImage = useCallback(async () => {
    setGeneratingStory(true);

    try {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Story dimensions
      canvas.width = 1080;
      canvas.height = 1920;

      // Background gradient
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
      gradient.addColorStop(0, "#1a1a1a");
      gradient.addColorStop(1, "#0a0a0a");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Load and draw product image
      if (product.primaryImage) {
        try {
          const img = new Image();
          img.crossOrigin = "anonymous";

          await new Promise<void>((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = () => reject(new Error("Image load failed"));
            img.src = product.primaryImage!;
          });

          // Draw image centered with padding
          const maxWidth = 900;
          const maxHeight = 900;
          const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
          const width = img.width * scale;
          const height = img.height * scale;
          const x = (canvas.width - width) / 2;
          const y = 300;

          // Add white background for image
          ctx.fillStyle = "#ffffff";
          ctx.roundRect(x - 20, y - 20, width + 40, height + 40, 20);
          ctx.fill();

          ctx.drawImage(img, x, y, width, height);
        } catch {
          // Continue without image
        }
      }

      // Product name
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 56px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.textAlign = "center";

      // Word wrap for long names
      const words = product.name.split(" ");
      let line = "";
      let lines: string[] = [];
      const maxLineWidth = 900;

      for (const word of words) {
        const testLine = line + word + " ";
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxLineWidth && line !== "") {
          lines.push(line.trim());
          line = word + " ";
        } else {
          line = testLine;
        }
      }
      lines.push(line.trim());

      let textY = 1300;
      for (const textLine of lines) {
        ctx.fillText(textLine, canvas.width / 2, textY);
        textY += 70;
      }

      // Price with accent color
      ctx.fillStyle = "#E85A4F";
      ctx.font = "bold 72px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText(formatPrice(product.price), canvas.width / 2, textY + 40);

      // Brand logo/text
      ctx.fillStyle = "#666666";
      ctx.font = "28px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("ihracfazlasigiyim.com", canvas.width / 2, 1750);

      // "Yukarı Kaydır" swipe up indicator
      ctx.fillStyle = "#ffffff";
      ctx.font = "24px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("Ürünü görmek için yukarı kaydır", canvas.width / 2, 1850);

      // Arrow up
      ctx.beginPath();
      ctx.moveTo(540, 1800);
      ctx.lineTo(520, 1820);
      ctx.lineTo(560, 1820);
      ctx.closePath();
      ctx.fill();

      // Convert to blob and download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          // Use product name for filename, slugified for safe filenames
          const safeFileName = slugify(product.name) || product.sku;
          a.download = `${safeFileName}-story.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
        setGeneratingStory(false);
      }, "image/png", 1.0);
    } catch {
      setGeneratingStory(false);
    }
  }, [product]);

  return (
    <div className="flex flex-col gap-3">
      {/* Instagram Share Button */}
      <button
        onClick={handleShare}
        className="flex items-center justify-center gap-2 w-full py-4 border border-[#E4405F] text-[#E4405F] rounded-full hover:bg-[#E4405F] hover:text-white transition-all"
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
        </svg>
        Instagram'da Paylas
      </button>

      {/* Story Image Generator */}
      <button
        onClick={generateStoryImage}
        disabled={generatingStory}
        className="flex items-center justify-center gap-2 w-full py-3 text-sm border border-gray-300 text-gray-600 rounded-full hover:bg-gray-50 transition-all disabled:opacity-50"
      >
        {generatingStory ? (
          <>
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Olusturuluyor...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Story Gorseli Indir
          </>
        )}
      </button>

      {/* Copy Link / QR Code Row */}
      <div className="flex gap-2">
        <button
          onClick={copyToClipboard}
          className="flex-1 flex items-center justify-center gap-2 py-3 text-sm border border-gray-300 text-gray-600 rounded-full hover:bg-gray-50 transition-all"
        >
          {copied ? (
            <>
              <svg className="w-4 h-4 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Kopyalandi!
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
              </svg>
              Linki Kopyala
            </>
          )}
        </button>

        <button
          onClick={() => setShowQR(!showQR)}
          className="px-4 py-3 text-sm border border-gray-300 text-gray-600 rounded-full hover:bg-gray-50 transition-all"
          title="QR Kod Goster"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75v-.75zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z" />
          </svg>
        </button>
      </div>

      {/* QR Code Display */}
      {showQR && (
        <div className="p-4 bg-white border border-gray-200 rounded-apple text-center">
          <p className="text-caption text-gray-500 mb-3">Telefonunuzla tarayin</p>
          {/* Simple QR Code using Google Charts API */}
          <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(fullUrl)}`}
            alt="QR Code"
            className="mx-auto"
            width={150}
            height={150}
          />
          <p className="text-caption text-gray-400 mt-2 truncate max-w-[200px] mx-auto">
            {fullUrl}
          </p>
        </div>
      )}
    </div>
  );
}
