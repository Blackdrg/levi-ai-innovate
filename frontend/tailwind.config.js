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
        sans: ['Outfit', 'sans-serif'],
      },
      colors: {
        neural: {
          bg: '#F8FAFC',
          secondary: '#F1F5F9',
          card: '#FFFFFF',
          text: '#0F172A',
          muted: '#64748B',
          border: '#E2E8F0',
          accentPrimary: '#6366F1',
          accentSecondary: '#22D3EE'
        },
        sovereign: {
          light: '#22D3EE',
          dark: '#4F46E5',
          accent: '#6366F1',
        }
      },
      animation: {
        'glow-pulse': 'glow 2s infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(99, 102, 241, 0.2)' },
          '50%': { boxShadow: '0 0 20px rgba(34, 211, 238, 0.4)' },
          '100%': { boxShadow: '0 0 5px rgba(99, 102, 241, 0.2)' },
        }
      }
    },
  },
  plugins: [],
}
