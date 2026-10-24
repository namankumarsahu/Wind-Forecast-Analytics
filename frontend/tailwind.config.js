/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f1f5fb",
          100: "#dce6f3",
          200: "#b9cde6",
          500: "#2f5588",
          600: "#244570",
          700: "#1a3558",
          800: "#122846",
          900: "#0b1d36",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
