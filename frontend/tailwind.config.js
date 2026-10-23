/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          main: '#0B0E14',
          sidebar: '#10141D',
          surface: '#151B26',
          elevated: '#1B2330',
        },
        border: {
          DEFAULT: '#293242',
          subtle: '#1E2A3A',
        },
        text: {
          primary: '#F3F5F9',
          secondary: '#A1ACBC',
          muted: '#788496',
        },
        accent: {
          primary: '#78E5C1',
          secondary: '#A5A0FF',
        },
        status: {
          warning: '#F2BE70',
          critical: '#FF777F',
          info: '#83B9FF',
          success: '#78E5C1',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
