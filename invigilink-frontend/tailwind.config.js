/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: "#2563eb",
        ink: "#111827",
        subtext: "#6b7280",
        card: "#0b1220",
        cardBorder: "rgba(255,255,255,0.08)",
      },
    },
  },
  plugins: [],
};
