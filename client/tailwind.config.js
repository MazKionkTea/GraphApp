/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          base: "#0d1117",
          panel: "#161b22",
          elevated: "#1c2128",
          hover: "#22272e",
        },
        border: {
          DEFAULT: "#30363d",
          soft: "#21262d",
        },
        fg: {
          DEFAULT: "#e6edf3",
          secondary: "#9da7b3",
          muted: "#6e7681",
        },
        accent: {
          DEFAULT: "#58a6ff",
          soft: "rgba(88,166,255,0.12)",
        },
        type: {
          package: "#3fb950",
          module: "#58a6ff",
          class: "#d29922",
          function: "#39c5cf",
          method: "#bc8cff",
          external: "#6e7681",
        },
      },
    },
  },
  plugins: [],
};
