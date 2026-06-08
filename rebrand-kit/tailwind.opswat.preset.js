/* OPSWAT Tailwind preset — for rebranding Tailwind codebases.
   Usage in the target's tailwind.config.js:
     module.exports = { presets: [require('./rebrand-kit/tailwind.opswat.preset.js')], ... }
   Then map app classes onto these tokens (e.g. bg-primary, text-n-900, rounded-md).
   Tokens mirror the opswat-ui design system. */
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1d6bfc', hover: '#154fba', light: '#eff4ff', subtle: '#e1e9fe' },
        n: {
          100: '#f4f4f5', 200: '#e9eaeb', 300: '#d2d4d6', 400: '#bcbfc3', 500: '#a4a8ae',
          700: '#707682', 800: '#616875', 900: '#485161', 1100: '#1b273c', 1300: '#080f21',
        },
        success: { DEFAULT: '#008a00', bg: '#edf7ed' },
        warning: { DEFAULT: '#ed6706', bg: '#fef4ed' },
        error:   { DEFAULT: '#d00300', bg: '#fceded' },
        info:    { DEFAULT: '#1d6bfc', bg: '#eff4ff' },
        dark:    { 100: '#273454', 200: '#111f42', 300: '#081938', 400: '#040d1c' },
        nav:     { 100: '#f1f3f8', 300: '#dbe1f0', 500: '#cbd3e7' },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      fontSize: {
        display: ['32px', { lineHeight: '40px', fontWeight: '700' }],
        h1: ['24px', { lineHeight: '32px', fontWeight: '600' }],
        h2: ['20px', { lineHeight: '28px', fontWeight: '600' }],
        h3: ['16px', { lineHeight: '24px', fontWeight: '500' }],
        body1: ['14px', { lineHeight: '20px' }],
        body2: ['12px', { lineHeight: '16px' }],
        caption: ['11px', { lineHeight: '16px' }],
      },
      spacing: { '2xs': '4px', xs: '8px', sm: '16px', md: '24px', lg: '32px', xl: '40px', '2xl': '48px' },
      borderRadius: { sm: '4px', md: '6px', lg: '8px' },
      boxShadow: {
        'opswat-sm': '0 2px 8px rgba(27, 39, 60, 0.06)',
        'opswat-md': '0 2px 8px rgba(27, 39, 60, 0.15)',
        'opswat-focus': '0 0 0 2px #7eaafd',
      },
    },
  },
};
