/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:          '#0d1117',
        surface:     '#161b22',
        'surface-2': '#1c2129',
        'surface-3': '#21262d',
        border:      '#30363d',
        'border-l':  '#3d444e',
        text:        '#c9d1d9',
        muted:       '#8b949e',
        accent:      '#58a6ff',
        trusted:     '#238636',
        flagged:     '#d29922',
        quarantined: '#da3633',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      animation: {
        'fade-in-up':  'fadeInUp .35s ease both',
        'fade-in':     'fadeIn .25s ease both',
        'count-up':    'countUp .4s cubic-bezier(.34,1.56,.64,1) both',
        'fill-bar':    'fillBar .6s cubic-bezier(.34,1.12,.64,1) both',
        'pulse-slow':  'pulse 2.5s cubic-bezier(.4,0,.6,1) infinite',
        shimmer:       'shimmer 1.4s infinite linear',
      },
      keyframes: {
        fadeInUp:  { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        fadeIn:    { from: { opacity: '0' }, to: { opacity: '1' } },
        countUp:   { from: { opacity: '0', transform: 'scale(.92)' }, to: { opacity: '1', transform: 'scale(1)' } },
        fillBar:   { from: { width: '0%' } },
        shimmer:   { '0%': { backgroundPosition: '-200% center' }, '100%': { backgroundPosition: '200% center' } },
      },
      boxShadow: {
        'trusted':     '0 0 0 1px rgba(35,134,54,.3), 0 4px 20px rgba(35,134,54,.15)',
        'flagged':     '0 0 0 1px rgba(210,153,34,.3), 0 4px 20px rgba(210,153,34,.15)',
        'quarantined': '0 0 0 1px rgba(218,54,51,.3), 0 4px 20px rgba(218,54,51,.15)',
        'accent':      '0 0 0 1px rgba(88,166,255,.2), 0 4px 20px rgba(88,166,255,.1)',
        'card':        '0 1px 3px rgba(0,0,0,.3), 0 4px 12px rgba(0,0,0,.2)',
        'card-hover':  '0 4px 16px rgba(0,0,0,.4), 0 1px 3px rgba(0,0,0,.3)',
      },
    },
  },
  plugins: [],
};
