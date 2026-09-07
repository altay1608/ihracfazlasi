"use client";

import { useEffect, useRef } from "react";
import { animate, stagger } from "animejs";
import { useIsMobile } from "@/hooks/useIsMobile";
import { WHATSAPP_PHONE } from "@/lib/constants";
import { createWhatsAppLink } from "@/lib/utils";

export default function WhatsAppCTA() {
  const message = "Merhaba! Web sitenizden ulaşıyorum. Ürünleriniz hakkında bilgi almak istiyorum.";
  const whatsappLink = createWhatsAppLink(WHATSAPP_PHONE, message);
  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const iconRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLAnchorElement>(null);
  const isMobile = useIsMobile();

  // Entrance animation
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    container.style.opacity = "0";
    container.style.transform = "translateY(30px)";

    const icon = container.querySelector(".wca-icon") as HTMLElement;
    const title = container.querySelector(".wca-title") as HTMLElement;
    const desc = container.querySelector(".wca-desc") as HTMLElement;
    const btn = container.querySelector(".wca-btn") as HTMLElement;
    const phone = container.querySelector(".wca-phone") as HTMLElement;

    [title, desc, btn, phone].forEach((el) => {
      if (el) { el.style.opacity = "0"; el.style.transform = "translateY(15px)"; }
    });

    if (icon) { icon.style.opacity = "0"; icon.style.transform = "scale(0)"; }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Container entrance
            animate(container, {
              opacity: [0, 1],
              translateY: [30, 0],
              duration: isMobile ? 600 : 1000,
              ease: "outExpo",
            });

            // Icon bounce in
            if (icon) {
              animate(icon, {
                opacity: [0, 1],
                scale: [0, 1],
                duration: isMobile ? 500 : 800,
                delay: 200,
                ease: "outElastic(1, 0.5)",
              });
            }

            // Text elements stagger
            animate([title, desc, btn, phone].filter(Boolean), {
              opacity: [0, 1],
              translateY: [15, 0],
              duration: isMobile ? 500 : 800,
              delay: stagger(80, { start: 300 }),
              ease: "outExpo",
            });

            observer.disconnect();
          }
        });
      },
      { threshold: 0.15 }
    );

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [isMobile]);

  // Icon pulse animation
  useEffect(() => {
    if (!iconRef.current) return;

    const icon = iconRef.current;

    const pulse = () => {
      animate(icon, {
        scale: [1, 1.1, 1],
        duration: 2000,
        ease: "inOutSine",
        onComplete: () => {
          setTimeout(pulse, 1500);
        },
      });
    };

    setTimeout(pulse, 2000);
  }, []);

  // Button magnetic hover - DESKTOP ONLY
  useEffect(() => {
    if (isMobile || !btnRef.current) return;

    const btn = btnRef.current;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = btn.getBoundingClientRect();
      const x = (e.clientX - rect.left - rect.width / 2) * 0.15;
      const y = (e.clientY - rect.top - rect.height / 2) * 0.15;

      animate(btn, {
        translateX: x,
        translateY: y,
        duration: 200,
        ease: "outQuad",
      });
    };

    const handleMouseLeave = () => {
      animate(btn, {
        translateX: 0,
        translateY: 0,
        duration: 500,
        ease: "outElastic(1, 0.4)",
      });
    };

    btn.addEventListener("mousemove", handleMouseMove);
    btn.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      btn.removeEventListener("mousemove", handleMouseMove);
      btn.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [isMobile]);

  return (
    <section ref={sectionRef} className="py-10 sm:py-14 md:py-20 bg-white dark:bg-[#0a0a0a] relative overflow-hidden">
      {/* Background gradient orbs - desktop only */}
      <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-green-500/5 rounded-full blur-[100px] pointer-events-none hidden md:block" />
      <div className="absolute bottom-0 left-0 w-[250px] h-[250px] bg-green-500/3 rounded-full blur-[80px] pointer-events-none hidden md:block" />

      <div className="container-apple relative z-10 px-4 sm:px-6">
        <div
          ref={containerRef}
          className="bg-gradient-to-br from-success/10 to-success/5 rounded-2xl sm:rounded-apple p-6 sm:p-8 md:p-12 lg:p-16 text-center"
        >
          {/* WhatsApp Icon */}
          <div
            ref={iconRef}
            className="wca-icon w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 bg-success rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6 md:mb-8"
          >
            <svg className="w-7 h-7 sm:w-8 sm:h-8 md:w-10 md:h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
            </svg>
          </div>

          {/* Text */}
          <h2 className="wca-title text-xl sm:text-2xl md:text-headline font-semibold text-foreground dark:text-white mb-2 sm:mb-4">
            Sorularınız mı var?
          </h2>
          <p className="wca-desc text-sm sm:text-base md:text-body-large text-gray-500 max-w-xl mx-auto mb-5 sm:mb-6 md:mb-8">
            WhatsApp üzerinden bize ulaşın. Ürünler, bedenler ve teslimat hakkında
            tüm sorularınızı yanıtlayalım.
          </p>

          {/* Button */}
          <a
            ref={btnRef}
            href={whatsappLink}
            target="_blank"
            rel="noopener noreferrer"
            className="wca-btn btn-whatsapp inline-flex items-center justify-center gap-2 w-full sm:w-auto px-6 sm:px-8 py-3.5 sm:py-4 text-base sm:text-lg"
          >
            <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
            </svg>
            WhatsApp ile İletişime Geç
          </a>

          {/* Phone Number */}
          <p className="wca-phone text-xs sm:text-caption text-gray-500 mt-3 sm:mt-4">
            veya{" "}
            <a href="tel:+905384793696" className="text-accent hover:underline">
              0538 479 36 96
            </a>
            {" "}numarasından arayın
          </p>
        </div>
      </div>
    </section>
  );
}
