/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: "#142B4A",
        slate: "#294C70",
        blue: "#3478F6",
        teal: "#14B8A6",
        bg: "#F5F7FB",
        card: "#FFFFFF",
        text: "#172B4D",
        muted: "#64748B",
        border: "#E2E8F0",
        safe: "#16A34A",
        suspicious: "#F59E0B",
        attack: "#DC2626",
        quarantined: "#8B5CF6",
        approved: "#14B8A6",
      },
    },
  },
  plugins: [],
}
