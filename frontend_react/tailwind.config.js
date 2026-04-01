/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Outfit', 'sans-serif'],
      },
      colors: {
        sovereign: {
          light: '#9d50bb',
          dark: '#6e48aa',
          accent: '#00d2ff',
        }
      },
      animation: {
        'glow-pulse': 'glow 2s infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(157, 80, 187, 0.2)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 210, 255, 0.4)' },
          '100%': { boxShadow: '0 0 5px rgba(157, 80, 187, 0.2)' },
        }
      }
    },
  },
  plugins: [],
}
