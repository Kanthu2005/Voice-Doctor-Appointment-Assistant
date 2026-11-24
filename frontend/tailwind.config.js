/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      colors: {
        navy: {
          900: "#0F172A",
          800: "#1E293B",
          700: "#334155",
        },
        clinical: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          600: "#2563EB",
          700: "#1D4ED8",
        },
        tealcare: {
          50: "#F0FDFA",
          100: "#CCFBF1",
          600: "#0D9488",
          700: "#0F766E",
        },
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
        elevated: "0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 1px 3px 0 rgba(15, 23, 42, 0.04)",
      },
    },
  },
  plugins: [],
};
