import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        "bg-deep": "#0A0E17",
        "bg-surface": "#111827",
        "bg-elevated": "#1A2332",
        "bg-hover": "#1F2D3D",
        "text-primary": "#F1F5F9",
        "text-secondary": "#94A3B8",
        "text-muted": "#64748B",
        "accent-blue": "#3B82F6",
        "accent-cyan": "#06B6D4",
        "accent-emerald": "#10B981",
        "accent-amber": "#F59E0B",
        "accent-red": "#EF4444",
        "accent-violet": "#8B5CF6",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-in-left": "slideInLeft 0.3s ease-out",
        "fade-in": "fadeIn 0.2s ease-out",
        ticker: "ticker 30s linear infinite",
        "glow-pulse": "glowPulse 3s ease-in-out infinite",
        "count-up": "countUp 0.6s cubic-bezier(0.22, 1, 0.36, 1)",
        "shimmer": "shimmer 1.8s ease-in-out infinite",
        "border-glow": "gradientBorderRotate 4s ease infinite",
      },
      keyframes: {
        slideInRight: {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        slideInLeft: {
          "0%": { transform: "translateX(-100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        ticker: {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(-100%)" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 8px rgba(6, 182, 212, 0.2)" },
          "50%": { boxShadow: "0 0 20px rgba(6, 182, 212, 0.4)" },
        },
        countUp: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        gradientBorderRotate: {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
