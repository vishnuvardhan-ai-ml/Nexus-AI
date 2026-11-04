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
        navy: {
          950: '#070b14',
          900: '#0b1120',
          850: '#0d1527',
          800: '#10192e',
          700: '#1e293b',
          600: '#334155',
        },
        brand: {
          cyan: '#00f0ff',
          teal: '#06b6d4',
          sky: '#38bdf8',
          blue: '#3b82f6',
          indigo: '#6366f1',
        },
        risk: {
          low: '#10b981',
          medium: '#f59e0b',
          high: '#f43f5e',
          critical: '#ef4444',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 20px -5px rgba(0, 240, 255, 0.25)',
        'glow-blue': '0 0 20px -5px rgba(59, 130, 246, 0.3)',
        'glow-card': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'subtle-grid': 'radial-gradient(rgba(56, 189, 248, 0.08) 1px, transparent 1px)',
      }
    },
  },
  plugins: [],
}
