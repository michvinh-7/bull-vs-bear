import type { Config } from "tailwindcss";

// Colors follow the UI mockup: dark surfaces, blue bull, orange bear, violet moderator.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d1014",
        panel: "#161a20",
        line: "#262b33",
        bull: { DEFAULT: "#4f8ff7", bg: "#1b2a44" },
        bear: { DEFAULT: "#f0a04b", bg: "#3a2a16" },
        mod: { DEFAULT: "#b9a4f5", bg: "#1f1d26" },
        verified: "#4ade80",
        contested: "#facc15",
        unsupported: "#f87171",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
