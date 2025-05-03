/**
 * Tailwind CSS Configuration
 *
 * This file contains customizations for Tailwind CSS,
 * including theme extensions, custom colors, and plugins.
 */

window.tailwindConfig = {
  theme: {
    screens: {
      xs: "320px",
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    extend: {
      colors: {
        // Primary color palette (blue-based)
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
        // Brand colors for consistent styling
        brand: {
          green: "#10b981", // Main brand green (Emerald-500)
          blue: "#0ea5e9", // Brand blue (Same as primary-500)
          yellow: "#f59e0b", // Warning/attention color
          red: "#ef4444", // Error/negative color
        },
        // Semantic UI colors
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        info: "#3b82f6",
        // UI element colors
        "eco-green": "#10b981",
        "deep-forest": "#064e3b",
        "eco-green-5": "#f0fdfa",
        "slate-gray": "#64748b",
        "light-gray": "#e2e8f0",
        charcoal: "#1e293b",
        "snow-white": "#f8fafc",
      },
      fontFamily: {
        sans: ['"Noto Sans Thai"', "sans-serif"],
        headings: ['"Noto Sans Thai"', "sans-serif"],
        mono: ["monospace"],
      },
      spacing: {
        72: "18rem",
        84: "21rem",
        96: "24rem",
      },
      maxWidth: {
        "1/4": "25%",
        "1/2": "50%",
        "3/4": "75%",
        xs: "20rem",
      },
      boxShadow: {
        soft: "0 2px 10px rgba(0, 0, 0, 0.05)",
        card: "0 4px 8px rgba(0, 0, 0, 0.03), 0 1px 3px rgba(0, 0, 0, 0.05)",
        elevated:
          "0 10px 30px rgba(0, 0, 0, 0.08), 0 2px 10px rgba(0, 0, 0, 0.04)",
      },
      height: {
        "screen-fixed": "100vh",
        "screen-dynamic": "calc(var(--vh, 1vh) * 100)",
      },
      minHeight: {
        "screen-fixed": "100vh",
        "screen-dynamic": "calc(var(--vh, 1vh) * 100)",
      },
      borderRadius: {
        card: "0.5rem",
        button: "0.375rem",
        tag: "0.25rem",
      },
      animation: {
        "status-pulse": "status-pulse 1.5s infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-in": "slide-in 0.3s ease-out",
      },
      keyframes: {
        "status-pulse": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.6 },
        },
        "fade-in": {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        "slide-in": {
          "0%": { transform: "translateY(-10px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
      },
      transitionDuration: {
        400: "400ms",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        pattern: 'url("/static/images/pattern-light.svg")',
      },
    },
  },
  variants: {
    extend: {
      display: ["responsive", "hover", "focus", "group-hover"],
      opacity: ["responsive", "hover", "focus", "group-hover"],
      scale: ["responsive", "hover", "focus", "active"],
      translate: ["responsive", "hover", "focus", "active"],
      backgroundColor: [
        "responsive",
        "hover",
        "focus",
        "active",
        "group-hover",
      ],
      textColor: ["responsive", "hover", "focus", "active", "group-hover"],
      borderColor: ["responsive", "hover", "focus", "active"],
      ringColor: ["responsive", "hover", "focus", "active"],
      ringWidth: ["responsive", "hover", "focus", "active"],
    },
  },
  plugins: [],
};
