/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          verylow: "#16a34a",
          low: "#65a30d",
          moderate: "#eab308",
          high: "#ea580c",
          critical: "#dc2626",
        },
      },
    },
  },
  plugins: [],
}
