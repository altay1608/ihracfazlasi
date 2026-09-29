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
    image: "/images/categories/ust-giyim.webp",
    href: "/urunler?kategori=ust-giyim",
  },
  {
    name: "Alt Giyim",
    slug: "alt-giyim",
    description: "Pantolon, jean, şort",
    image: "/images/categories/alt-giyim.webp",
    href: "/urunler?kategori=alt-giyim",
  },
  {
    name: "Aksesuar",
    slug: "aksesuar",
    description: "Kemer, çanta, cüzdan, şapka",
    image: "/images/categories/aksesuar.webp",
    href: "/urunler?kategori=aksesuar",
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
          <p className="cat-subtitle text-sm sm:text-base md:text-body-large text-gray-500 dark:text-stone-400">
            Aradığınız tarzı bulun
          </p>
        </div>

        {/* Category Grid */}
        <div ref={gridRef} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
          {categories.map((category) => (
            <CategoryCard key={category.slug} category={category} />
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
  image: string;
  href: string;
}

function CategoryCard({ category }: { category: CategoryType }) {
  return (
    <Link
      href={category.href}
      className="category-card group block relative h-[340px] sm:h-[390px] md:h-[440px] lg:h-[460px] rounded-2xl sm:rounded-[28px] overflow-hidden bg-stone-950 shadow-[0_24px_70px_-34px_rgba(0,0,0,0.65)] ring-1 ring-black/5 dark:ring-white/10"
    >
      {/* Local, optimized editorial image */}
      <div className="absolute inset-0 overflow-hidden">
        <Image
          src={category.image}
          alt={category.name}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, 33vw"
          className="cat-img object-cover transition-transform duration-700 ease-out group-hover:scale-[1.035]"
        />
      </div>

      {/* Consistent contrast layer */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/25 to-black/5" />

      {/* Hover overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-500" />

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-6 md:p-8 text-white">
        <div className="transform transition-transform duration-500 group-hover:-translate-y-1">
          <span className="mb-3 inline-flex items-center gap-2 text-[10px] sm:text-xs font-semibold uppercase tracking-[0.2em] text-amber-200/90">
            <span className="h-px w-6 bg-amber-200/70" />
            Erkek Koleksiyonu
          </span>

          <h3 className="text-2xl sm:text-3xl md:text-[2rem] font-semibold mb-1.5 sm:mb-2 tracking-tight">{category.name}</h3>
          <p className="text-sm sm:text-base text-white/75 mb-4 sm:mb-5">{category.description}</p>

          {/* Arrow button */}
          <div className="inline-flex items-center gap-2 sm:gap-3 text-white/80 group-hover:text-white transition-colors">
            <span className="text-xs sm:text-sm font-semibold tracking-wide">Koleksiyonu Gör</span>
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full border border-white/30 group-hover:border-amber-200/80 group-hover:bg-amber-200 group-hover:text-stone-950 flex items-center justify-center transition-all duration-300">
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
