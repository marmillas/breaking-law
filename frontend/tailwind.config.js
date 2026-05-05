/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          50: '#f9f6ef',
          100: '#f0e9d8',
          200: '#e2d3b3',
          300: '#d4bd8e',
          400: '#c6a769',
          500: '#b8965a',
          600: '#a0804d',
          700: '#8a6b41',
          800: '#745635',
          900: '#5e4229',
        },
        sepia: {
          50: '#faf8f3',
          100: '#f5f0e6',
          200: '#ebe2d0',
          300: '#e0d4ba',
          400: '#d6c6a4',
          500: '#ccba8f',
          600: '#b8a47d',
          700: '#a08e6b',
          800: '#88785a',
          900: '#706248',
        },
        sidebar: {
          DEFAULT: '#1a1a1a',
          light: '#2a2a2a',
        },
        semantic: {
          success: '#2d6a4f',
          warning: '#bc6c25',
          info: '#264653',
          danger: '#9b2226',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        heading: ['Libre Baskerville', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
