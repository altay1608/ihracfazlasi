"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useIsMobile } from "@/hooks/useIsMobile";

export default function Hero() {
  const [loadVideo, setLoadVideo] = useState(false);
  const isMobile = useIsMobile();

  // Keep the first paint light: load the large desktop video only after the
  // page is interactive. Mobile devices never request this file.
  useEffect(() => {
    if (isMobile) {
      setLoadVideo(false);
      return;
    }

    const windowWithIdle = window as Window & {
      requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
      cancelIdleCallback?: (id: number) => void;
    };
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    let idleId: number | undefined;

    if (windowWithIdle.requestIdleCallback) {
      idleId = windowWithIdle.requestIdleCallback(() => setLoadVideo(true), { timeout: 1200 });
    } else {
      timeoutId = setTimeout(() => setLoadVideo(true), 600);
    }

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (idleId !== undefined) windowWithIdle.cancelIdleCallback?.(idleId);
    };
  }, [isMobile]);

  return (
    <section
      className="relative overflow-hidden"
      style={{ height: "100svh", minHeight: "560px", maxHeight: isMobile ? "none" : "900px" }}
    >
      {/* Instant fallback shown while the desktop video is loading */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-gray-950 via-gray-900 to-gray-800" />
        {/* Mobil Dekoratif Elementler */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-[80px]" />
        <div className="absolute bottom-20 left-0 w-48 h-48 bg-blue-400/8 rounded-full blur-[60px]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-80 h-80 bg-indigo-600/5 rounded-full blur-[100px]" />
      </div>

      {/* Desktop için video - parallax layer */}
      {loadVideo && (
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          className="hero-video absolute inset-0 w-full h-full object-cover hidden md:block"
        >
          <source src="/hero-video.webm" type="video/webm" media="(min-width: 768px)" />
        </video>
      )}

      {/* Dark Overlay */}
      <div className="hero-overlay absolute inset-0 bg-gradient-to-b from-black/50 via-black/40 to-black/70" />

      {/* Animated grain/noise overlay - desktop only */}
      <div className="absolute inset-0 opacity-[0.03] bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIj48ZmlsdGVyIGlkPSJhIiB4PSIwIiB5PSIwIj48ZmVUdXJidWxlbmNlIGJhc2VGcmVxdWVuY3k9Ii43NSIgc3RpdGNoVGlsZXM9InN0aXRjaCIgdHlwZT0iZnJhY3RhbE5vaXNlIi8+PC9maWx0ZXI+PHJlY3Qgd2lkdGg9IjMwMCIgaGVpZ2h0PSIzMDAiIGZpbHRlcj0idXJsKCNhKSIgb3BhY2l0eT0iMSIvPjwvc3ZnPg==')] hidden md:block" />

      {/* Gradient Lines - DESKTOP ONLY */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none hidden md:block">
        <div className="absolute left-1/4 top-0 w-px h-full bg-gradient-to-b from-transparent via-white/10 to-transparent" />
        <div className="absolute left-2/4 top-0 w-px h-full bg-gradient-to-b from-transparent via-white/5 to-transparent" />
        <div className="absolute left-3/4 top-0 w-px h-full bg-gradient-to-b from-transparent via-white/10 to-transparent" />
      </div>

      {/* Content */}
      <div className="hero-content relative z-10 h-full flex flex-col items-center justify-center text-center px-5 sm:px-6">
        <div className="max-w-5xl w-full">
          {/* Badge with shimmer */}
          <div
            className="relative inline-flex items-center gap-2 px-4 py-2 sm:px-5 sm:py-2.5 bg-white/10 backdrop-blur-md rounded-full border border-white/20 mb-6 sm:mb-8 overflow-hidden"
          >
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse flex-shrink-0" />
            <span className="text-xs sm:text-sm text-white/90 font-medium whitespace-nowrap">Bursa İnegöl&apos;den Türkiye&apos;ye</span>
          </div>

          {/* Title */}
          <h1
            className="text-4xl xs:text-5xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-semibold text-white tracking-tight mb-4 sm:mb-6 leading-[1.1]"
          >
            <span className="hero-word inline-block">Dünya&nbsp;</span>
            <span className="hero-word inline-block">Markalarında</span>
            <br />
            <span className="hero-word inline-block bg-gradient-to-r from-white via-blue-200 to-white bg-clip-text text-transparent">
              Erkek&nbsp;
            </span>
            <span className="hero-word inline-block bg-gradient-to-r from-blue-200 via-white to-blue-200 bg-clip-text text-transparent">
              Giyim
            </span>
          </h1>

          {/* Brands - mobilde daha az göster */}
          <div className="flex flex-wrap items-center justify-center gap-x-2 sm:gap-x-3 gap-y-1.5 mb-4 sm:mb-5">
            {["Prada", "Lacoste", "Tommy Hilfiger", "Hugo Boss", "Armani", "Calvin Klein"].map((brand, i) => (
              <span
                key={brand}
                className="hero-brand text-xs sm:text-base md:text-lg lg:text-xl text-white/75 font-light"
              >
                {brand}
                {i < 5 && <span className="text-white/30 ml-1.5 sm:ml-3">•</span>}
              </span>
            ))}
          </div>

          <p
            className="text-sm sm:text-base md:text-lg text-white/60 max-w-sm sm:max-w-xl mx-auto mb-7 sm:mb-10 px-2 leading-relaxed"
          >
            İhraç fazlası ithal ürünler, uygun fiyatlarla.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col xs:flex-row items-center justify-center gap-3 sm:gap-4 px-2">
            <Link
              href="/urunler"
              className="hero-btn group relative w-full xs:w-auto px-7 sm:px-8 py-4 sm:py-4 bg-white text-black font-semibold text-base sm:text-lg rounded-full overflow-hidden transition-shadow duration-300 hover:shadow-[0_0_40px_rgba(255,255,255,0.3)] text-center min-w-[200px] xs:min-w-0"
            >
              <span className="relative z-10">Ürünleri Keşfet</span>
              <div className="absolute inset-0 bg-gradient-to-r from-blue-100 via-white to-blue-100 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </Link>
            <Link
              href="/hakkimizda"
              className="hero-btn w-full xs:w-auto px-7 sm:px-8 py-4 sm:py-4 bg-transparent text-white font-medium text-base sm:text-lg rounded-full border border-white/30 hover:border-white/60 hover:bg-white/10 transition-all duration-300 backdrop-blur-sm text-center min-w-[200px] xs:min-w-0"
            >
              Hakkımızda
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 sm:gap-8 md:gap-16 max-w-xs sm:max-w-xl mx-auto mt-10 sm:mt-16 md:mt-20 px-2">
          <StatItem value="10+" label="Dünya Markası" />
          <StatItem value="5.0" label="Google (58 yorum)" hasStar />
          <StatItem value="%100" label="İthal Ürün" />
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-6 sm:bottom-8 left-1/2 -translate-x-1/2">
        <ScrollIndicator />
      </div>
    </section>
  );
}

function StatItem({ value, label, hasStar }: { value: string; label: string; hasStar?: boolean }) {
  return (
    <div className="hero-stat text-center">
      <div className="flex items-center justify-center gap-0.5 sm:gap-1">
        <span className="text-lg sm:text-2xl md:text-3xl font-semibold text-white leading-none">{value}</span>
        {hasStar && (
          <svg className="w-3.5 h-3.5 sm:w-5 sm:h-5 text-yellow-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        )}
      </div>
      <p className="text-[9px] xs:text-[10px] sm:text-xs md:text-sm text-white/50 mt-1 leading-tight">{label}</p>
    </div>
  );
}

function ScrollIndicator() {
  return (
    <div className="w-6 h-10 rounded-full border-2 border-white/30 flex items-start justify-center p-2">
      <div className="w-1 h-2 bg-white/60 rounded-full animate-bounce" />
    </div>
  );
}
