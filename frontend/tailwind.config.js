/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#040814',
        'background-alt': '#060c1d',
        surface: '#0a1226',
        'surface-elevated': '#0f1a36',
        'surface-glass': 'rgba(10, 18, 38, 0.75)',
        'surface-mesh': 'rgba(7, 14, 30, 0.85)',
        border: 'rgba(255, 255, 255, 0.08)',
        'border-subtle': 'rgba(255, 255, 255, 0.05)',
        'border-focus': 'rgba(0, 201, 255, 0.5)',
        brand: {
          50: '#e0f7ff',
          100: '#b8eeff',
          200: '#7ae1ff',
          300: '#38d2ff',
          400: '#00c9ff',
          500: '#007cff',
          600: '#0062d1',
          700: '#004aa6',
          800: '#00337a',
          900: '#002052',
        },
        mesh: {
          cyan: '#00c9ff',
          blue: '#007cff',
          teal: '#00e599',
          purple: '#7928ca',
          pink: '#ff0080',
          dark: '#040814',
          card: '#081022',
        },
        accent: {
          cyan: '#00c9ff',
          emerald: '#00e599',
          amber: '#f59e0b',
          rose: '#f43f5e',
          violet: '#8b5cf6',
          indigo: '#6366f1',
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glow-brand': '0 0 35px -5px rgba(0, 124, 255, 0.35)',
        'glow-cyan': '0 0 35px -5px rgba(0, 201, 255, 0.35)',
        'glow-emerald': '0 0 35px -5px rgba(0, 229, 153, 0.35)',
        'glow-purple': '0 0 35px -5px rgba(121, 40, 202, 0.35)',
        'mesh-card': '0 12px 30px -10px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.08)',
        'mesh-card-hover': '0 20px 40px -15px rgba(0, 201, 255, 0.25), 0 0 0 1px rgba(0, 201, 255, 0.3)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float-slow': 'float 6s ease-in-out infinite',
        'beam': 'beam 8s linear infinite',
        'shimmer': 'shimmer 2.5s linear infinite',
        'marquee': 'mesh-marquee 32s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        beam: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(200%)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        }
      }
    },
  },
  plugins: [],
}
