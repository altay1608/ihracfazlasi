import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    screens: {
      xs: "390px",
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    extend: {
      colors: {
        background: "#ffffff",
        foreground: "#1d1d1f",
        "gray-100": "#f5f5f7",
        "gray-200": "#e8e8ed",
        "gray-500": "#86868b",
        "gray-700": "#424245",
        accent: "#0071e3",
        "accent-hover": "#0077ED",
        success: "#34c759",
        "success-hover": "#2db84d",
      },
      fontFamily: {
        sans: [
          "SF Pro Display",
          "SF Pro Text",
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      fontSize: {
        "display-large": ["80px", { lineHeight: "1.05", letterSpacing: "-0.015em", fontWeight: "600" }],
        "display": ["56px", { lineHeight: "1.07", letterSpacing: "-0.015em", fontWeight: "600" }],
        "headline": ["40px", { lineHeight: "1.1", letterSpacing: "-0.01em", fontWeight: "600" }],
        "title": ["28px", { lineHeight: "1.14", letterSpacing: "-0.007em", fontWeight: "600" }],
        "body-large": ["21px", { lineHeight: "1.38", fontWeight: "400" }],
        "body": ["17px", { lineHeight: "1.47", fontWeight: "400" }],
        "caption": ["14px", { lineHeight: "1.43", fontWeight: "400" }],
      },
      spacing: {
        "section": "120px",
        "section-sm": "80px",
      },
      borderRadius: {
        "apple": "18px",
        "apple-sm": "12px",
      },
      boxShadow: {
        "apple": "0 4px 24px rgba(0, 0, 0, 0.08)",
        "apple-hover": "0 8px 32px rgba(0, 0, 0, 0.12)",
      },
      transitionTimingFunction: {
        "apple": "cubic-bezier(0.25, 0.1, 0.25, 1)",
      },
      transitionDuration: {
        "apple": "400ms",
      },
    },
  },
  plugins: [],
} satisfies Config;
