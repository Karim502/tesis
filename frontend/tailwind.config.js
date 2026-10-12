/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14232B",
        panel: "#12353A",
        accent: "#1F5F5B",
        riesgo: { bajo: "#2F7D4F", medio: "#A16207", alto: "#B3261E" },
      },
      fontFamily: { sans: ['"Schibsted Grotesk"', "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
