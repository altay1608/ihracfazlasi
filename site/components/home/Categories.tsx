"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { animate, stagger } from "animejs";
import { useIsMobile } from "@/hooks/useIsMobile";

const categories = [
  {
    name: "Üst Giyim",
    slug: "ust-giyim",
    description: "T-shirt, gömlek, kazak, ceket",
    brands: ["Prada", "Lacoste", "Tommy Hilfiger", "Hugo Boss"],
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&q=90&fit=crop",
    href: "/urunler?kategori=ust-giyim",
    gradient: "from-blue-900/80 via-blue-900/40 to-transparent",
    accent: "bg-blue-500",
  },
  {
    name: "Alt Giyim",
    slug: "alt-giyim",
    description: "Pantolon, jean, şort",
    brands: ["Calvin Klein", "Armani", "Ralph Lauren"],
    image: "https://images.unsplash.com/photo-1542272604-787c3835535d?w=800&q=90&fit=crop",
    href: "/urunler?kategori=alt-giyim",
    gradient: "from-stone-900/80 via-stone-900/40 to-transparent",
    accent: "bg-amber-500",
  },
  {
    name: "Aksesuar",
    slug: "aksesuar",
    description: "Kemer, çanta, cüzdan, şapka",
    brands: ["Prada", "Gucci", "Versace", "Burberry"],
    image: "https://images.unsplash.com/photo-1614164185128-e4ec99c436d7?w=800&q=90&fit=crop",
    href: "/urunler?kategori=aksesuar",
    gradient: "from-amber-950/80 via-amber-950/40 to-transparent",
    accent: "bg-emerald-500",
  },
];

export default function Categories() {
  const sectionRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  // Header animation on scroll
  useEffect(() => {
    if (!headerRef.current) return;

    const badge = headerRef.current.querySelector(".cat-badge");
    const title = headerRef.current.querySelector(".cat-title");
    const subtitle = headerRef.current.querySelector(".cat-subtitle");

    [badge, title, subtitle].forEach((el) => {
      if (el) {
        (el as HTMLElement).style.opacity = "0";
        (el as HTMLElement).style.transform = "translateY(20px)";
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animate([badge, title, subtitle].filter(Boolean), {
              opacity: [0, 1],
              translateY: [20, 0],
              duration: isMobile ? 600 : 1000,
              delay: stagger(isMobile ? 80 : 150),
              ease: "outExpo",
            });
            observer.disconnect();
          }
        });
      },
      { threshold: 0.15 }
    );

    observer.observe(headerRef.current);
    return () => observer.disconnect();
  }, [isMobile]);

  // Cards animation with stagger
  useEffect(() => {
    if (!gridRef.current) return;

    const cards = gridRef.current.querySelectorAll(".category-card");
    cards.forEach((card) => {
      (card as HTMLElement).style.opacity = "0";
      (card as HTMLElement).style.transform = `translateY(${isMobile ? 30 : 60}px)`;
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animate(cards, {
              opacity: [0, 1],
              translateY: [isMobile ? 30 : 60, 0],
              duration: isMobile ? 700 : 1200,
              delay: stagger(isMobile ? 120 : 200),
              ease: "outExpo",
            });
            observer.disconnect();
          }
        });
      },
      { threshold: 0.05 }
    );

    observer.observe(gridRef.current);
    return () => observer.disconnect();
  }, [isMobile]);

  // Parallax effect on category images - DESKTOP ONLY
  useEffect(() => {
    if (isMobile || !gridRef.current) return;

    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const cards = gridRef.current?.querySelectorAll(".category-card");
          cards?.forEach((card) => {
            const rect = card.getBoundingClientRect();
            const windowHeight = window.innerHeight;

            if (rect.top < windowHeight && rect.bottom > 0) {
              const progress = (windowHeight - rect.top) / (windowHeight + rect.height);
              const offset = (progress - 0.5) * 40;
              const img = card.querySelector(".cat-img") as HTMLElement;
              if (img) {
                img.style.transform = `translateY(${offset}px) scale(1.1)`;
              }
            }
          });

          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener("scroll", handleScroll);
  }, [isMobile]);

  return (
    <section ref={sectionRef} className="py-12 sm:py-16 md:py-20 bg-white dark:bg-[#0a0a0a] relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 pointer-events-none hidden md:block">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent/3 rounded-full blur-[150px]" />
      </div>

      <div className="container-wide relative z-10 px-4 sm:px-6">
        {/* Header */}
        <div ref={headerRef} className="text-center mb-8 sm:mb-12 md:mb-16">
          <div className="cat-badge inline-flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 bg-gray-100 dark:bg-white/5 rounded-full mb-4 sm:mb-6">
            <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 font-medium">Koleksiyonları Keşfet</span>
          </div>
          <h2 className="cat-title text-2xl sm:text-3xl md:text-4xl lg:text-display font-semibold text-foreground dark:text-white mb-2 sm:mb-4">
            Kategoriler
          </h2>
          <p className="cat-subtitle text-sm sm:text-base md:text-body-large text-gray-500">
            Aradığınız tarzı bulun
          </p>
        </div>

        {/* Category Grid */}
        <div ref={gridRef} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
          {categories.map((category) => (
            <CategoryCard key={category.slug} category={category} isMobile={isMobile} />
          ))}
        </div>
      </div>
    </section>
  );
}

interface CategoryType {
  name: string;
  slug: string;
  description: string;
  brands: string[];
  image: string;
  href: string;
  gradient: string;
  accent: string;
}

function CategoryCard({ category, isMobile }: { category: CategoryType; isMobile: boolean }) {
  const cardRef = useRef<HTMLAnchorElement>(null);

  // Card hover tilt effect - DESKTOP ONLY
  useEffect(() => {
    if (isMobile) return;

    const card = cardRef.current;
    if (!card) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;

      animate(card, {
        rotateY: x * 8,
        rotateX: -y * 8,
        duration: 400,
        ease: "outQuad",
      });

      const glow = card.querySelector(".card-glow") as HTMLElement;
      if (glow) {
        glow.style.left = `${e.clientX - rect.left}px`;
        glow.style.top = `${e.clientY - rect.top}px`;
        glow.style.opacity = "1";
      }
    };

    const handleMouseLeave = () => {
      animate(card, {
        rotateY: 0,
        rotateX: 0,
        duration: 600,
        ease: "outExpo",
      });

      const glow = card.querySelector(".card-glow") as HTMLElement;
      if (glow) {
        glow.style.opacity = "0";
      }
    };

    card.addEventListener("mousemove", handleMouseMove);
    card.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      card.removeEventListener("mousemove", handleMouseMove);
      card.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [isMobile]);

  return (
    <Link
      ref={cardRef}
      href={category.href}
      className="category-card group block relative h-[300px] sm:h-[360px] md:h-[420px] lg:h-[480px] rounded-2xl sm:rounded-apple overflow-hidden"
      style={!isMobile ? { perspective: "1000px", transformStyle: "preserve-3d" } : undefined}
    >
      {/* Image with parallax */}
      <div className="absolute inset-0 overflow-hidden">
        <Image
          src={category.image}
          alt={category.name}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, 33vw"
          className="cat-img object-cover transition-transform duration-700 ease-out"
          style={{ transform: "scale(1.1)" }}
        />
      </div>

      {/* Gradient Overlay */}
      <div className={`absolute inset-0 bg-gradient-to-t ${category.gradient}`} />
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

      {/* Hover glow - DESKTOP ONLY */}
      {!isMobile && (
        <div
          className="card-glow absolute w-40 h-40 bg-white/20 rounded-full blur-[60px] -translate-x-1/2 -translate-y-1/2 pointer-events-none transition-opacity duration-300"
          style={{ opacity: 0 }}
        />
      )}

      {/* Hover overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-500" />

      {/* Category badge */}
      <div className="absolute top-4 left-4 sm:top-6 sm:left-6">
        <div className={`w-2 h-2 ${category.accent} rounded-full`} />
      </div>

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-6 md:p-8 text-white">
        <div className="transform transition-transform duration-500 group-hover:translate-y-[-4px] sm:group-hover:translate-y-[-8px]">
          {/* Brand tags */}
          <div className="flex flex-wrap gap-1 sm:gap-1.5 mb-3 sm:mb-4">
            {category.brands.slice(0, isMobile ? 3 : 4).map((brand) => (
              <span
                key={brand}
                className="px-2 py-0.5 sm:px-2.5 sm:py-1 text-[10px] sm:text-[11px] font-semibold tracking-wide uppercase bg-white/15 backdrop-blur-sm rounded-full border border-white/10 text-white/90"
              >
                {brand}
              </span>
            ))}
          </div>

          <h3 className="text-xl sm:text-2xl md:text-3xl font-semibold mb-1 sm:mb-2 tracking-tight">{category.name}</h3>
          <p className="text-sm sm:text-base text-white/70 mb-3 sm:mb-5">{category.description}</p>

          {/* Arrow button */}
          <div className="inline-flex items-center gap-2 sm:gap-3 text-white/80 group-hover:text-white transition-colors">
            <span className="text-xs sm:text-sm font-medium tracking-wide uppercase">Keşfet</span>
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full border border-white/30 group-hover:border-white/60 group-hover:bg-white/10 flex items-center justify-center transition-all duration-300">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-3.5 h-3.5 sm:w-4 sm:h-4 transition-transform group-hover:translate-x-0.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
