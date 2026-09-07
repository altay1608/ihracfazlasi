// Anime.js V4 utility hooks for parallax and scroll animations
// These hooks provide reusable animation patterns

"use client";

import { useEffect, useRef } from "react";
import { animate, stagger } from "animejs";

// Hook: Parallax scroll effect
export function useParallax<T extends HTMLElement>(speed: number = 0.5) {
    const ref = useRef<T>(null);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        let ticking = false;

        const handleScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    const rect = el.getBoundingClientRect();
                    const windowHeight = window.innerHeight;
                    const elementCenter = rect.top + rect.height / 2;
                    const offset = (elementCenter - windowHeight / 2) * speed;
                    el.style.transform = `translateY(${offset}px)`;
                    ticking = false;
                });
                ticking = true;
            }
        };

        window.addEventListener("scroll", handleScroll, { passive: true });
        handleScroll();

        return () => window.removeEventListener("scroll", handleScroll);
    }, [speed]);

    return ref;
}

// Hook: Scroll-triggered stagger animation
export function useScrollStagger<T extends HTMLElement>(
    childSelector: string,
    staggerDelay: number = 80,
    options?: { threshold?: number }
) {
    const ref = useRef<T>(null);
    const hasAnimated = useRef(false);

    useEffect(() => {
        const container = ref.current;
        if (!container) return;

        const { threshold = 0.1 } = options || {};
        const children = container.querySelectorAll(childSelector);

        children.forEach((child) => {
            const el = child as HTMLElement;
            el.style.opacity = "0";
            el.style.transform = "translateY(40px)";
        });

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting && !hasAnimated.current) {
                        hasAnimated.current = true;

                        animate(children, {
                            opacity: [0, 1],
                            translateY: [40, 0],
                            duration: 800,
                            delay: stagger(staggerDelay),
                            ease: "outExpo",
                        });
                    }
                });
            },
            { threshold }
        );

        observer.observe(container);
        return () => observer.disconnect();
    }, [childSelector, staggerDelay, options]);

    return ref;
}

// Hook: Magnetic hover effect
export function useMagneticHover<T extends HTMLElement>(strength: number = 0.3) {
    const ref = useRef<T>(null);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        const handleMouseMove = (e: MouseEvent) => {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            animate(el, {
                translateX: x * strength,
                translateY: y * strength,
                duration: 300,
                ease: "outQuad",
            });
        };

        const handleMouseLeave = () => {
            animate(el, {
                translateX: 0,
                translateY: 0,
                duration: 500,
                ease: "outExpo",
            });
        };

        el.addEventListener("mousemove", handleMouseMove);
        el.addEventListener("mouseleave", handleMouseLeave);

        return () => {
            el.removeEventListener("mousemove", handleMouseMove);
            el.removeEventListener("mouseleave", handleMouseLeave);
        };
    }, [strength]);

    return ref;
}
