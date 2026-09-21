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
        // Custom palette
        'dark': {
          950: '#222f38',  // Noir bleuté (dark bg)
          900: '#2a3a48',
          800: '#3a4a58',
          700: '#41505a',  // Gris foncé
        },
        'light': {
          50: '#ffffff',   // Blanc (light bg)
          100: '#f8f8f8',
          200: '#e6e0e6',  // Gris très clair
        },
        'neutral': {
          600: '#73828e',  // Gris moyen (text secondary)
          700: '#41505a',  // Gris foncé (text primary dark)
        },
        'accent': {
          red: '#EC3432',    // Rouge bright (highlights)
          'red-600': '#ca2216', // Rouge moyen
          'red-700': '#af1f11', // Rouge foncé
          gold: '#f06a67',   // Red secondary accent
        },
        'primary': {
          500: '#e64040',    // Red primary action
          600: '#c92f32',
          700: '#a9252a',
        },
      },
      fontFamily: {
        sans: ['Verdana', 'system-ui', 'sans-serif'],
      },
      spacing: {
        'gap': '1rem', // Confortable
      },
    },
  },
  plugins: [],
}
