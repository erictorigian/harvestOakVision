/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#1C1C1E',
        surface:  '#2C2C2E',
        elevated: '#3A3A3C',
        sep:      'rgba(84,84,88,0.65)',
        secondary:'rgba(235,235,245,0.6)',
        tertiary: 'rgba(235,235,245,0.3)',
        green:  '#30D158',
        red:    '#FF453A',
        orange: '#FF9F0A',
        blue:   '#0A84FF',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        mono: ['"SF Mono"', '"JetBrains Mono"', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },
    },
  },
  plugins: [],
}
