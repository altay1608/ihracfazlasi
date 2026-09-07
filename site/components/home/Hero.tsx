"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { animate, stagger, createTimeline } from "animejs";
import { useIsMobile } from "@/hooks/useIsMobile";

export default function Hero() {
  const heroRef = useRef<HTMLElement>(null);
  const particlesRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);
  const brandsRef = useRef<HTMLDivElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const statsRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const isMobile = useIsMobile();

  // Parallax scroll effect - DESKTOP ONLY
  useEffect(() => {
    if (isMobile) return;

    const hero = heroRef.current;
    if (!hero) return;

    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          const heroHeight = hero.offsetHeight;

          if (scrollY < heroHeight) {
            const progress = scrollY / heroHeight;

            const video = hero.querySelector(".hero-video") as HTMLElement;
            const overlay = hero.querySelector(".hero-overlay") as HTMLElement;
            const content = hero.querySelector(".hero-content") as HTMLElement;

            if (video) video.style.transform = `translateY(${scrollY * 0.4}px) scale(${1 + progress * 0.1})`;
            if (overlay) overlay.style.opacity = String(0.4 + progress * 0.4);
            if (content) {
              content.style.transform = `translateY(${scrollY * -0.2}px)`;
              content.style.opacity = String(1 - progress * 1.5);
            }
          }

          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isMobile]);

  // Initial entrance animations
  useEffect(() => {
    setMounted(true);

    const mobileDuration = isMobile ? 600 : 1200;
    const mobileDelay = isMobile ? 100 : 300;

    const tl = createTimeline({
      defaults: {
        ease: "outExpo",
        duration: mobileDuration,
      },
    });

    // Badge slides in
    if (badgeRef.current) {
      badgeRef.current.style.opacity = "0";
      badgeRef.current.style.transform = "translateY(15px)";
      tl.add(badgeRef.current, {
        opacity: [0, 1],
        translateY: [15, 0],
        duration: isMobile ? 500 : 800,
      }, mobileDelay);
    }

    // Title reveals
    if (titleRef.current) {
      const words = titleRef.current.querySelectorAll(".hero-word");
      words.forEach((w) => {
        (w as HTMLElement).style.opacity = "0";
        (w as HTMLElement).style.transform = `translateY(${isMobile ? 30 : 60}px)`;
      });
      tl.add(words, {
        opacity: [0, 1],
        translateY: [isMobile ? 30 : 60, 0],
        duration: isMobile ? 600 : 1000,
        delay: stagger(isMobile ? 80 : 120),
      }, isMobile ? 200 : 500);
    }

    // Brands cascade in
    if (brandsRef.current) {
      const brandEls = brandsRef.current.querySelectorAll(".hero-brand");
      brandEls.forEach((b) => {
        (b as HTMLElement).style.opacity = "0";
        (b as HTMLElement).style.transform = "translateY(10px)";
      });
      tl.add(brandEls, {
        opacity: [0, 1],
        translateY: [10, 0],
        duration: isMobile ? 400 : 600,
        delay: stagger(isMobile ? 40 : 60, { from: "center" }),
      }, isMobile ? 600 : 1200);
    }

    // Subtitle fades in
    if (subtitleRef.current) {
      subtitleRef.current.style.opacity = "0";
      subtitleRef.current.style.transform = "translateY(10px)";
      tl.add(subtitleRef.current, {
        opacity: [0, 1],
        translateY: [10, 0],
        duration: isMobile ? 500 : 800,
      }, isMobile ? 800 : 1600);
    }

    // CTA buttons
    if (ctaRef.current) {
      const buttons = ctaRef.current.querySelectorAll(".hero-btn");
      buttons.forEach((b) => {
        (b as HTMLElement).style.opacity = "0";
        (b as HTMLElement).style.transform = "translateY(20px)";
      });
      tl.add(buttons, {
        opacity: [0, 1],
        translateY: [20, 0],
        duration: isMobile ? 500 : 800,
        delay: stagger(100),
      }, isMobile ? 900 : 1800);
    }

    // Stats
    if (statsRef.current) {
      const statItems = statsRef.current.querySelectorAll(".hero-stat");
      statItems.forEach((s) => {
        (s as HTMLElement).style.opacity = "0";
        (s as HTMLElement).style.transform = "translateY(20px)";
      });
      tl.add(statItems, {
        opacity: [0, 1],
        translateY: [20, 0],
        duration: isMobile ? 500 : 800,
        delay: stagger(80),
      }, isMobile ? 1000 : 2000);
    }

    // Scroll indicator
    if (scrollRef.current) {
      scrollRef.current.style.opacity = "0";
      tl.add(scrollRef.current, {
        opacity: [0, 1],
        duration: 600,
      }, isMobile ? 1200 : 2500);
    }

    // Floating particles - DESKTOP ONLY
    if (!isMobile && particlesRef.current) {
      const particles = particlesRef.current.querySelectorAll(".particle");
      animate(particles, {
        translateY: () => [-20, 20],
        translateX: () => [-15, 15],
        opacity: [0.2, 0.6, 0.2],
        scale: [0.8, 1.2, 0.8],
        duration: () => 3000 + Math.random() * 4000,
        delay: stagger(200),
        loop: true,
        alternate: true,
        ease: "inOutSine",
      });
    }
  }, [isMobile]);

  // Magnetic effect for CTA buttons - DESKTOP ONLY
  useEffect(() => {
    if (isMobile || !ctaRef.current) return;

    const buttons = ctaRef.current.querySelectorAll(".hero-btn");

    const handleMouseMove = (e: Event) => {
      const mouseEvent = e as MouseEvent;
      const btn = mouseEvent.currentTarget as HTMLElement;
      const rect = btn.getBoundingClientRect();
      const x = mouseEvent.clientX - rect.left - rect.width / 2;
      const y = mouseEvent.clientY - rect.top - rect.height / 2;

      animate(btn, {
        translateX: x * 0.2,
        translateY: y * 0.2,
        duration: 300,
        ease: "outQuad",
      });
    };

    const handleMouseLeave = (e: Event) => {
      const btn = e.currentTarget as HTMLElement;
      animate(btn, {
        translateX: 0,
        translateY: 0,
        duration: 600,
        ease: "outElastic(1, 0.4)",
      });
    };

    buttons.forEach((btn) => {
      btn.addEventListener("mousemove", handleMouseMove);
      btn.addEventListener("mouseleave", handleMouseLeave);
    });

    return () => {
      buttons.forEach((btn) => {
        btn.removeEventListener("mousemove", handleMouseMove);
        btn.removeEventListener("mouseleave", handleMouseLeave);
      });
    };
  }, [isMobile]);

  // Shimmer loop on badge - DESKTOP ONLY
  useEffect(() => {
    if (isMobile || !badgeRef.current) return;

    const shimmer = badgeRef.current.querySelector(".badge-shimmer") as HTMLElement;
    if (!shimmer) return;

    const runShimmer = () => {
      animate(shimmer, {
        translateX: ["-200%", "200%"],
        duration: 1500,
        ease: "linear",
        onComplete: () => {
          setTimeout(runShimmer, 3000);
        },
      });
    };

    setTimeout(runShimmer, 2000);
  }, [isMobile]);

  return (
    <section
      ref={heroRef}
      className="relative overflow-hidden"
      style={{ height: "100svh", minHeight: "560px", maxHeight: isMobile ? "none" : "900px" }}
    >
      {/* Mobil için zengin gradient arka plan */}
      <div className="absolute inset-0 md:hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-gray-950 via-gray-900 to-gray-800" />
        {/* Mobil Dekoratif Elementler */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-[80px]" />
        <div className="absolute bottom-20 left-0 w-48 h-48 bg-blue-400/8 rounded-full blur-[60px]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-80 h-80 bg-indigo-600/5 rounded-full blur-[100px]" />
      </div>

      {/* Desktop için video - parallax layer */}
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="hero-video absolute inset-0 w-full h-full object-cover hidden md:block"
      >
        <source src="/hero-video.webm" type="video/webm" />
      </video>

      {/* Dark Overlay */}
      <div className="hero-overlay absolute inset-0 bg-gradient-to-b from-black/50 via-black/40 to-black/70" />

      {/* Floating Particles - DESKTOP ONLY */}
      {!isMobile && (
        <div ref={particlesRef} className="absolute inset-0 overflow-hidden pointer-events-none hidden md:block">
          {mounted && [...Array(15)].map((_, i) => (
            <div
              key={i}
              className="particle absolute w-1 h-1 bg-white/20 rounded-full"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                width: `${2 + Math.random() * 4}px`,
                height: `${2 + Math.random() * 4}px`,
              }}
            />
          ))}
        </div>
      )}

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
            ref={badgeRef}
            className="relative inline-flex items-center gap-2 px-4 py-2 sm:px-5 sm:py-2.5 bg-white/10 backdrop-blur-md rounded-full border border-white/20 mb-6 sm:mb-8 overflow-hidden"
          >
            {!isMobile && (
              <div className="badge-shimmer absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent -skew-x-12" style={{ transform: "translateX(-200%)" }} />
            )}
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse flex-shrink-0" />
            <span className="text-xs sm:text-sm text-white/90 font-medium whitespace-nowrap">Bursa İnegöl&apos;den Türkiye&apos;ye</span>
          </div>

          {/* Title */}
          <h1
            ref={titleRef}
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
          <div ref={brandsRef} className="flex flex-wrap items-center justify-center gap-x-2 sm:gap-x-3 gap-y-1.5 mb-4 sm:mb-5">
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
            ref={subtitleRef}
            className="text-sm sm:text-base md:text-lg text-white/60 max-w-sm sm:max-w-xl mx-auto mb-7 sm:mb-10 px-2 leading-relaxed"
          >
            İhraç fazlası ithal ürünler, uygun fiyatlarla.
          </p>

          {/* CTA Buttons */}
          <div ref={ctaRef} className="flex flex-col xs:flex-row items-center justify-center gap-3 sm:gap-4 px-2">
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
        <div ref={statsRef} className="grid grid-cols-3 gap-3 sm:gap-8 md:gap-16 max-w-xs sm:max-w-xl mx-auto mt-10 sm:mt-16 md:mt-20 px-2">
          <StatItem value="10+" label="Dünya Markası" />
          <StatItem value="5.0" label="Google (58 yorum)" hasStar />
          <StatItem value="%100" label="İthal Ürün" />
        </div>
      </div>

      {/* Scroll Indicator */}
      <div ref={scrollRef} className="absolute bottom-6 sm:bottom-8 left-1/2 -translate-x-1/2">
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
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const dot = ref.current.querySelector(".scroll-dot") as HTMLElement;
    if (!dot) return;

    animate(dot, {
      translateY: [0, 12, 0],
      opacity: [0.3, 1, 0.3],
      duration: 1500,
      loop: true,
      ease: "inOutSine",
    });

    animate(ref.current, {
      translateY: [0, 8, 0],
      duration: 2000,
      loop: true,
      ease: "inOutQuad",
    });
  }, []);

  return (
    <div ref={ref} className="w-6 h-10 rounded-full border-2 border-white/30 flex items-start justify-center p-2">
      <div className="scroll-dot w-1 h-2 bg-white/60 rounded-full" />
    </div>
  );
}
