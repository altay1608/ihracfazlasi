"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";
import { BRANDS } from "@/lib/constants";

export default function BrandMarquee() {
    const sectionRef = useRef<HTMLElement>(null);
    const trackRef = useRef<HTMLDivElement>(null);
    const allBrands = [...BRANDS, ...BRANDS, ...BRANDS];

    // Entrance animation
    useEffect(() => {
        if (!sectionRef.current) return;

        sectionRef.current.style.opacity = "0";

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate(sectionRef.current!, {
                            opacity: [0, 1],
                            duration: 800,
                            ease: "outExpo",
                        });
                        observer.disconnect();
                    }
                });
            },
            { threshold: 0.2 }
        );

        observer.observe(sectionRef.current);
        return () => observer.disconnect();
    }, []);

    // Infinite scroll animation
    useEffect(() => {
        if (!trackRef.current) return;

        const track = trackRef.current;
        const totalWidth = track.scrollWidth / 3;

        animate(track, {
            translateX: [0, -totalWidth],
            duration: 30000,
            ease: "linear",
            loop: true,
        });
    }, []);

    return (
        <section
            ref={sectionRef}
            className="relative py-4 sm:py-6 md:py-8 bg-gray-50 dark:bg-[#111] overflow-hidden border-y border-gray-200 dark:border-gray-800"
        >
            {/* Gradient fade edges */}
            <div className="absolute left-0 top-0 bottom-0 w-12 sm:w-20 md:w-24 bg-gradient-to-r from-gray-50 dark:from-[#111] to-transparent z-10" />
            <div className="absolute right-0 top-0 bottom-0 w-12 sm:w-20 md:w-24 bg-gradient-to-l from-gray-50 dark:from-[#111] to-transparent z-10" />

            {/* Scrolling brands */}
            <div
                ref={trackRef}
                className="flex items-center gap-6 sm:gap-8 md:gap-12 whitespace-nowrap"
            >
                {allBrands.map((brand, i) => (
                    <span
                        key={`${brand}-${i}`}
                        className="text-sm sm:text-base md:text-lg lg:text-xl font-semibold text-gray-400 dark:text-gray-500 tracking-wide uppercase select-none flex-shrink-0 cursor-default"
                    >
                        {brand}
                    </span>
                ))}
            </div>
        </section>
    );
}
