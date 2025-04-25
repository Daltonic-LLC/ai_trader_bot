/** @type {import('tailwindcss').Config} */
const config = {
    content: ['./pages/**/*.{tsx,ts}', './components/**/*.{tsx,ts}'],
    theme: {
      extend: {
        fontFamily: {
          poppins: ['Poppins', 'sans-serif'],
        },
        colors: {
          'crypto-dark': '#0F172A', // Dark background
          'crypto-blue': '#3B82F6', // Neon blue
          'crypto-green': '#10B981', // Neon green
          'crypto-gray': '#1E293B', // Card background
        },
      },
    },
    plugins: [],
  };

export default config;