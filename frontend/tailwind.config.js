/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef5fc',
          100: '#d9e9f8',
          200: '#b8d7f3',
          300: '#86bdeb',
          400: '#4e9ede',
          500: '#2580ce',
          600: '#1765b2',
          700: '#145190',
          800: '#144577',
          900: '#163b63',
          950: '#0e2542',
        },
        portalNavy: {
          dark: '#0b192c',
          card: '#102542',
          header: '#1e3a5f'
        },
        portalBlue: {
          action: '#1d63dc',
          hover: '#1854bc',
          border: '#3b82f6'
        },
        portalGreen: {
          action: '#22a047',
          hover: '#1b853a'
        }
      },
    },
  },
  plugins: [],
}
