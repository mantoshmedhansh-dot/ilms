/**
 * ILMS.AI Theme Configuration
 *
 * Clean, professional SaaS design system
 * Indigo & Slate palette
 */

export const theme = {
  // Primary Colors
  colors: {
    // Indigo - Primary brand color
    indigo: {
      50: '#EEF2FF',
      100: '#E0E7FF',
      200: '#C7D2FE',
      300: '#A5B4FC',
      400: '#818CF8',
      500: '#6366F1',  // Main indigo
      600: '#5C6BC0',
      700: '#4338CA',
      800: '#3730A3',
      900: '#312E81',
    },
    // Slate - Neutral palette
    slate: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',
      900: '#0F172A',
      950: '#020617',
    },
  },

  // Gradient combinations
  gradients: {
    indigoDark: 'linear-gradient(135deg, #312E81 0%, #6366F1 100%)',
    darkCard: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)',
    hero: 'linear-gradient(135deg, #0F172A 0%, #312E81 50%, #0F172A 100%)',
  },

  // Semantic colors
  semantic: {
    success: '#10B981',
    error: '#EF4444',
    warning: '#F59E0B',
    info: '#6366F1',
  },

  // Typography
  fonts: {
    heading: '"Inter", "Segoe UI", sans-serif',
    body: '"Inter", "Segoe UI", sans-serif',
  },
} as const;

// Tailwind CSS class mappings for dark theme
export const darkThemeClasses = {
  // Backgrounds
  bgPrimary: 'bg-slate-900',
  bgSecondary: 'bg-slate-800',
  bgCard: 'bg-slate-800/50',
  bgHover: 'hover:bg-slate-700',

  // Text
  textPrimary: 'text-white',
  textSecondary: 'text-slate-300',
  textMuted: 'text-slate-400',
  textAccent: 'text-indigo-400',
  textBlue: 'text-blue-500',

  // Borders
  borderDefault: 'border-slate-700',
  borderAccent: 'border-indigo-500',
  borderBlue: 'border-blue-600',

  // Buttons
  btnPrimary: 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold',
  btnSecondary: 'bg-slate-700 hover:bg-slate-600 text-white',
  btnOutline: 'border-indigo-500 text-indigo-400 hover:bg-indigo-500 hover:text-white',
  btnGhost: 'text-slate-300 hover:text-white hover:bg-slate-700',

  // Cards
  card: 'bg-slate-800/50 border border-slate-700 rounded-xl',
  cardHover: 'hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10',

  // Inputs
  input: 'bg-slate-800 border-slate-600 text-white placeholder:text-slate-400 focus:border-indigo-500 focus:ring-indigo-500/20',

  // Badges
  badgeAccent: 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
  badgeBlue: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  badgeSuccess: 'bg-emerald-500/20 text-emerald-400',
  badgeDiscount: 'bg-red-500 text-white',
};

// CSS Variables for global styles
export const cssVariables = `
  :root {
    --color-indigo: #6366F1;
    --color-indigo-light: #818CF8;
    --color-indigo-dark: #4338CA;
    --color-blue: #2563EB;
    --color-blue-light: #3B82F6;
    --color-blue-dark: #1E3A8A;
    --color-bg-primary: #0F172A;
    --color-bg-secondary: #1E293B;
    --color-bg-card: #1E293B80;
    --color-text-primary: #FFFFFF;
    --color-text-secondary: #CBD5E1;
    --color-text-muted: #94A3B8;
    --color-border: #334155;
  }
`;

export default theme;
