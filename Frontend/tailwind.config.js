/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        gh: {
          bg: '#0a150a',
          card: '#0f1f0f',
          border: '#1e3a1e',
          muted: '#4a7a4a',
          accent: '#4ade80',
        },
      },
    },
  },
  plugins: [],
}
