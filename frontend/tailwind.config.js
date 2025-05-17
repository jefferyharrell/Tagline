/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        jlla: {
          red: '#d32a40',  // JL Red
          black: '#000000', // For type
          white: '#ffffff', // For background
        },
        // Map Tailwind's default colors to JLLA's colors
        primary: {
          DEFAULT: '#d32a40', // JL Red as primary
          foreground: '#ffffff' // White text on red
        },
      },
      backgroundColor: theme => ({
        ...theme('colors'),
        'jlla-red': '#d32a40',
        'jlla-white': '#ffffff',
      }),
      textColor: theme => ({
        ...theme('colors'),
        'jlla-black': '#000000',
        'jlla-red': '#d32a40',
      }),
      borderColor: theme => ({
        ...theme('colors'),
        'jlla-red': '#d32a40',
      }),
      ringColor: theme => ({
        ...theme('colors'),
        'jlla-red': 'rgba(211, 42, 64, 0.5)',
      }),
    },
  },
  plugins: [],
}
