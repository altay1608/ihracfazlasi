"use client";

import { useEffect, useRef } from "react";
import { animate, stagger } from "animejs";
import { useIsMobile } from "@/hooks/useIsMobile";

const trustItems = [
    {
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 sm:w-7 sm:h-7">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
        ),
        title: "%100 Orijinal",
        description: "Tüm ürünlerimiz orijinal ithal ürünlerdir",
    },
    {
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 sm:w-7 sm:h-7">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
        ),
        title: "Hızlı Kargo",
        description: "Türkiye geneline 1-3 iş günü teslimat",
    },
    {
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 sm:w-7 sm:h-7">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
            </svg>
        ),
        title: "Uygun Fiyat",
        description: "İhraç fazlası avantajıyla dünya markaları",
    },
    {
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 sm:w-7 sm:h-7">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
            </svg>
        ),
        title: "5.0 ★ Google",
        description: "58 müşteri değerlendirmesiyle tam puan",
    },
];

export default function TrustBadges() {
    const sectionRef = useRef<HTMLElement>(null);
    const headerRef = useRef<HTMLDivElement>(null);
    const gridRef = useRef<HTMLDivElement>(null);
    const isMobile = useIsMobile();

    // Header animation
    useEffect(() => {
        if (!headerRef.current) return;

        const title = headerRef.current.querySelector(".trust-title") as HTMLElement;
        const subtitle = headerRef.current.querySelector(".trust-subtitle") as HTMLElement;
        if (title) { title.style.opacity = "0"; title.style.transform = "translateY(20px)"; }
        if (subtitle) { subtitle.style.opacity = "0"; subtitle.style.transform = "translateY(20px)"; }

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate([title, subtitle].filter(Boolean), {
                            opacity: [0, 1],
                            translateY: [20, 0],
                            duration: isMobile ? 600 : 900,
                            delay: stagger(100),
                            ease: "outExpo",
                        });
                        observer.disconnect();
                    }
                });
            },
            { threshold: 0.2 }
        );

        observer.observe(headerRef.current);
        return () => observer.disconnect();
    }, [isMobile]);

    // Cards stagger animation
    useEffect(() => {
        if (!gridRef.current) return;

        const cards = gridRef.current.querySelectorAll(".trust-card");
        cards.forEach((card) => {
            (card as HTMLElement).style.opacity = "0";
            (card as HTMLElement).style.transform = `translateY(${isMobile ? 25 : 50}px)`;
        });

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate(cards, {
                            opacity: [0, 1],
                            translateY: [isMobile ? 25 : 50, 0],
                            duration: isMobile ? 600 : 1000,
                            delay: stagger(isMobile ? 80 : 120, isMobile ? undefined : { from: "center" }),
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

    // Icon bounce on hover - DESKTOP ONLY
    useEffect(() => {
        if (isMobile || !gridRef.current) return;

        const cards = gridRef.current.querySelectorAll(".trust-card");

        const handleMouseEnter = (e: Event) => {
            const card = e.currentTarget as HTMLElement;
            const icon = card.querySelector(".trust-icon") as HTMLElement;
            if (icon) {
                animate(icon, {
                    scale: [1, 1.2, 1.1],
                    rotate: [0, -10, 10, 0],
                    duration: 600,
                    ease: "outElastic(1, 0.5)",
                });
            }
        };

        cards.forEach((card) => {
            card.addEventListener("mouseenter", handleMouseEnter);
        });

        return () => {
            cards.forEach((card) => {
                card.removeEventListener("mouseenter", handleMouseEnter);
            });
        };
    }, [isMobile]);

    // Parallax floating effect - DESKTOP ONLY
    useEffect(() => {
        if (isMobile || !gridRef.current) return;

        let ticking = false;

        const handleScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    const cards = gridRef.current?.querySelectorAll(".trust-card");
                    cards?.forEach((card, i) => {
                        const rect = card.getBoundingClientRect();
                        const windowHeight = window.innerHeight;
                        if (rect.top < windowHeight && rect.bottom > 0) {
                            const progress = (windowHeight - rect.top) / (windowHeight + rect.height);
                            const offset = (progress - 0.5) * 15 * (i % 2 === 0 ? 1 : -1);
                            (card as HTMLElement).style.transform = `translateY(${offset}px)`;
                        }
                    });
                    ticking = false;
                });
                ticking = true;
            }
        };

        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, [isMobile]);

    return (
        <section ref={sectionRef} className="py-10 sm:py-14 md:py-20 bg-white dark:bg-[#0a0a0a] relative overflow-hidden">
            {/* Background glow - desktop only */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[120px] pointer-events-none hidden md:block" />

            <div className="container-wide relative z-10 px-4 sm:px-6">
                <div ref={headerRef} className="text-center mb-8 sm:mb-12">
                    <h2 className="trust-title text-2xl sm:text-3xl md:text-headline font-semibold text-foreground dark:text-white mb-2 sm:mb-3">Neden Biz?</h2>
                    <p className="trust-subtitle text-sm sm:text-base md:text-body-large text-gray-500">
                        Güvenle alışveriş yapmanız için 4 sebep
                    </p>
                </div>

                <div ref={gridRef} className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6">
                    {trustItems.map((item) => (
                        <div
                            key={item.title}
                            className="trust-card group relative bg-gray-50 dark:bg-[#161616] rounded-xl sm:rounded-apple p-4 sm:p-6 md:p-8 text-center hover:bg-gradient-to-br hover:from-accent/5 hover:to-accent/10 dark:hover:from-accent/10 dark:hover:to-accent/20 transition-all duration-500 border border-transparent hover:border-accent/20"
                        >
                            {/* Glow effect on hover - desktop only */}
                            <div className="absolute inset-0 rounded-apple opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-accent/5 to-transparent blur-xl hidden md:block" />

                            <div className="relative">
                                <div className="trust-icon inline-flex items-center justify-center w-11 h-11 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-accent/10 dark:bg-accent/20 text-accent mb-3 sm:mb-5 transition-transform duration-300">
                                    {item.icon}
                                </div>
                                <h3 className="text-sm sm:text-base md:text-lg font-semibold text-foreground dark:text-white mb-1 sm:mb-2">
                                    {item.title}
                                </h3>
                                <p className="text-xs sm:text-sm text-gray-500 leading-relaxed">
                                    {item.description}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
