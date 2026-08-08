/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: "#0b0f17",
          800: "#131b2a",
          700: "#1e293b",
          600: "#334155",
        },
        accent: {
          cyan: "#06b6d4",
          purple: "#8b5cf6",
          emerald: "#10b981",
          rose: "#f43f5e",
          amber: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
};
