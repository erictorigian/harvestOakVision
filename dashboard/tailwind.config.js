/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0D1117',
        panel:   '#161B22',
        border:  '#21262D',
        amber:   { DEFAULT: '#F59E0B', dim: '#92610A' },
        oak:     '#C8871A',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'monospace'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-once': 'pulse 0.4s ease-in-out 1',
        'blink':      'blink 1s step-end infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%':       { opacity: 0 },
        },
      },
    },
  },
  plugins: [],
}
