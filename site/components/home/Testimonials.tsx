"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { animate, stagger } from "animejs";
import { useIsMobile } from "@/hooks/useIsMobile";

const testimonials = [
    {
        name: "Ahmet Y.",
        location: "İstanbul",
        rating: 5,
        text: "Ürün kalitesi mükemmel, fiyatları piyasanın çok altında. Hugo Boss bir gömlek aldım, kumaş kalitesi bire bir aynı. Kesinlikle tekrar alışveriş yapacağım.",
        product: "Hugo Boss Gömlek",
    },
    {
        name: "Mehmet K.",
        location: "Ankara",
        rating: 5,
        text: "İlk defa ihraç fazlası ürün aldım ve çok memnun kaldım. Tommy Hilfiger kazağın kalitesi harika. Kargolama da çok hızlıydı.",
        product: "Tommy Hilfiger Kazak",
    },
    {
        name: "Oğuz T.",
        location: "Bursa",
        rating: 5,
        text: "Mağazaya bizzat gittim, ürünlerin hepsi orijinal. Fiyat-performans oranı muhteşem. Lacoste polo tişört aldım, etiketleri bile üzerinde.",
        product: "Lacoste Polo T-shirt",
    },
    {
        name: "Emre S.",
        location: "İzmir",
        rating: 5,
        text: "WhatsApp'tan sipariş verdim, aynı gün kargoya verildi. Prada kemerin kalitesi çok iyi, orijinalden ayırt edemezsiniz.",
        product: "Prada Kemer",
    },
    {
        name: "Burak D.",
        location: "Antalya",
        rating: 5,
        text: "Calvin Klein jean aldım, kumaş ve kesim mükemmel. Mağazada 3000₺ olan ürünü burada çok daha uygun fiyata buldum.",
        product: "Calvin Klein Jean",
    },
];

function StarRating({ rating }: { rating: number }) {
    return (
        <div className="flex items-center gap-0.5">
            {[...Array(rating)].map((_, i) => (
                <svg
                    key={i}
                    className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
            ))}
        </div>
    );
}

export default function Testimonials() {
    const [current, setCurrent] = useState(0);
    const [isAutoPlaying, setIsAutoPlaying] = useState(true);
    const sectionRef = useRef<HTMLElement>(null);
    const headerRef = useRef<HTMLDivElement>(null);
    const cardRef = useRef<HTMLDivElement>(null);
    const dotsRef = useRef<HTMLDivElement>(null);
    const isMobile = useIsMobile();

    // Header entrance animation
    useEffect(() => {
        if (!headerRef.current) return;

        const badge = headerRef.current.querySelector(".test-badge") as HTMLElement;
        const title = headerRef.current.querySelector(".test-title") as HTMLElement;
        const subtitle = headerRef.current.querySelector(".test-subtitle") as HTMLElement;

        [badge, title, subtitle].forEach((el) => {
            if (el) { el.style.opacity = "0"; el.style.transform = "translateY(20px)"; }
        });

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate([badge, title, subtitle].filter(Boolean), {
                            opacity: [0, 1],
                            translateY: [20, 0],
                            duration: isMobile ? 600 : 1000,
                            delay: stagger(isMobile ? 80 : 120),
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

    // Card transition animation
    useEffect(() => {
        if (!cardRef.current) return;

        const card = cardRef.current;
        card.style.opacity = "0";
        card.style.transform = "translateY(15px)";

        animate(card, {
            opacity: [0, 1],
            translateY: [15, 0],
            duration: isMobile ? 400 : 700,
            ease: "outExpo",
        });
    }, [current, isMobile]);

    // Auto-play
    useEffect(() => {
        if (!isAutoPlaying) return;
        const timer = setInterval(() => {
            setCurrent((prev) => (prev + 1) % testimonials.length);
        }, 5000);
        return () => clearInterval(timer);
    }, [isAutoPlaying]);

    const goTo = useCallback((index: number) => {
        setCurrent(index);
        setIsAutoPlaying(false);
        setTimeout(() => setIsAutoPlaying(true), 10000);
    }, []);

    // Touch swipe support for mobile
    useEffect(() => {
        if (!isMobile || !cardRef.current) return;

        let startX = 0;
        let startY = 0;

        const handleTouchStart = (e: TouchEvent) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        };

        const handleTouchEnd = (e: TouchEvent) => {
            const diffX = e.changedTouches[0].clientX - startX;
            const diffY = e.changedTouches[0].clientY - startY;

            // Only swipe if horizontal movement is greater than vertical
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                if (diffX > 0) {
                    // Swipe right - previous
                    setCurrent((prev) => (prev - 1 + testimonials.length) % testimonials.length);
                } else {
                    // Swipe left - next
                    setCurrent((prev) => (prev + 1) % testimonials.length);
                }
                setIsAutoPlaying(false);
                setTimeout(() => setIsAutoPlaying(true), 10000);
            }
        };

        const card = cardRef.current;
        card.addEventListener("touchstart", handleTouchStart, { passive: true });
        card.addEventListener("touchend", handleTouchEnd, { passive: true });

        return () => {
            card.removeEventListener("touchstart", handleTouchStart);
            card.removeEventListener("touchend", handleTouchEnd);
        };
    }, [isMobile, current]);

    // Dots animation
    useEffect(() => {
        if (!dotsRef.current) return;

        const dots = dotsRef.current.querySelectorAll(".test-dot");
        dots.forEach((dot, i) => {
            const el = dot as HTMLElement;
            if (i === current) {
                animate(el, {
                    width: isMobile ? 24 : 32,
                    opacity: 1,
                    duration: 400,
                    ease: "outExpo",
                });
            } else {
                animate(el, {
                    width: 8,
                    opacity: 0.5,
                    duration: 400,
                    ease: "outExpo",
                });
            }
        });
    }, [current, isMobile]);

    return (
        <section
            ref={sectionRef}
            className="py-12 sm:py-16 md:py-20 lg:py-28 bg-gradient-to-b from-gray-50 to-white dark:from-[#111] dark:to-[#0a0a0a] overflow-hidden relative"
        >
            {/* Background decorative - desktop only */}
            <div className="absolute top-0 left-1/4 w-[400px] h-[400px] bg-yellow-500/3 rounded-full blur-[150px] pointer-events-none hidden md:block" />
            <div className="absolute bottom-0 right-1/4 w-[300px] h-[300px] bg-accent/3 rounded-full blur-[120px] pointer-events-none hidden md:block" />

            <div className="container-wide relative z-10 px-4 sm:px-6">
                {/* Header */}
                <div ref={headerRef} className="text-center mb-8 sm:mb-10 md:mb-14">
                    <div className="test-badge inline-flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-4 sm:py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-full mb-4 sm:mb-6">
                        <svg className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        <span className="text-xs sm:text-sm font-medium text-yellow-700 dark:text-yellow-400">
                            Google&apos;da 5.0 Puan
                        </span>
                    </div>
                    <h2 className="test-title text-2xl sm:text-3xl md:text-headline font-semibold text-foreground dark:text-white mb-2 sm:mb-3">
                        Müşterilerimiz Ne Diyor?
                    </h2>
                    <p className="test-subtitle text-sm sm:text-base md:text-body-large text-gray-500">
                        58 Google yorumundan bazıları
                    </p>
                </div>

                {/* Testimonial Card */}
                <div className="relative max-w-3xl mx-auto">
                    <div
                        ref={cardRef}
                        className="bg-white dark:bg-[#161616] rounded-2xl sm:rounded-apple p-6 sm:p-8 md:p-12 shadow-lg sm:shadow-apple text-center relative"
                    >
                        {/* Quote icon */}
                        <div className="absolute top-4 left-5 sm:top-6 sm:left-8 text-accent/10 dark:text-accent/20">
                            <svg className="w-8 h-8 sm:w-12 sm:h-12" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zM0 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151C7.546 6.068 5.983 8.789 5.983 11H10v10H0z" />
                            </svg>
                        </div>

                        <StarRating rating={testimonials[current].rating} />

                        <p className="text-base sm:text-lg md:text-xl text-foreground dark:text-white leading-relaxed mt-4 sm:mt-6 mb-6 sm:mb-8 font-light">
                            &ldquo;{testimonials[current].text}&rdquo;
                        </p>

                        <div className="flex items-center justify-center gap-2.5 sm:gap-3">
                            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center text-xs sm:text-sm font-semibold text-white flex-shrink-0">
                                {testimonials[current].name.charAt(0)}
                            </div>
                            <div className="text-left">
                                <p className="font-medium text-foreground dark:text-white text-xs sm:text-sm">
                                    {testimonials[current].name}
                                </p>
                                <p className="text-[10px] sm:text-xs text-gray-500">
                                    {testimonials[current].location} • {testimonials[current].product}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Swipe hint for mobile */}
                    {isMobile && (
                        <p className="text-center text-[10px] text-gray-400 mt-3">← Kaydırarak yorumları gezin →</p>
                    )}

                    {/* Dots */}
                    <div ref={dotsRef} className="flex items-center justify-center gap-1.5 sm:gap-2 mt-5 sm:mt-8">
                        {testimonials.map((_, index) => (
                            <button
                                key={index}
                                onClick={() => goTo(index)}
                                className={`test-dot h-2 rounded-full transition-colors duration-300 ${index === current
                                        ? "bg-accent"
                                        : "bg-gray-300 dark:bg-gray-600 hover:bg-gray-400"
                                    }`}
                                style={{
                                    width: index === current ? (isMobile ? 24 : 32) : 8,
                                    opacity: index === current ? 1 : 0.5,
                                }}
                                aria-label={`Yorum ${index + 1}`}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
