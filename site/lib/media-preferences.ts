export function shouldLoadDecorativeVideo(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(max-width: 767px), (prefers-reduced-motion: reduce)").matches) return false;
  const connection = (navigator as Navigator & {
    connection?: { saveData?: boolean; effectiveType?: string };
  }).connection;
  return !connection?.saveData && !["slow-2g", "2g", "3g"].includes(connection?.effectiveType || "");
}
