/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Shared Scomp palette from the project design rules.
        'dark': {
          950: '#222f38',
          900: '#293b45',
          800: '#293b45',
          700: '#314954',
        },
        'light': {
          50: '#f3f5f4',
          100: '#e8eeeb',
          200: '#d5dfda',
        },
        'neutral': {
          600: '#a7b3bb',
          700: '#41505a',
        },
        'accent': {
          red: '#ec3432',
          'red-600': '#c52b2a',
          'red-700': '#9f2221',
          gold: '#d7be7d',
        },
        'primary': {
          500: '#d7be7d',
          600: '#ceab5d',
          700: '#a98b4d',
        },
        success: '#d7be7d',
        warning: '#ceab5d',
        danger: '#ec3432',
      },
      fontFamily: {
        sans: ['Avenir Next', 'Segoe UI', 'sans-serif'],
      },
      spacing: {
        'gap': '1rem', // Confortable
      },
    },
  },
  plugins: [],
}
