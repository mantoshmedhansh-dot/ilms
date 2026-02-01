/**
 * Aquapurite Theme Configuration
 *
 * Dark mode theme with Golden and Blue accents
 * Inspired by: Eureka Forbes, Atomberg, Havells
 */

export const theme = {
  // Primary Colors
  colors: {
    // Golden - Primary brand color
    gold: {
      50: '#FFFBEB',
      100: '#FEF3C7',
      200: '#FDE68A',
      300: '#FCD34D',
      400: '#FBBF24',
      500: '#F59E0B',  // Main gold
      600: '#D97706',
      700: '#B45309',
      800: '#92400E',
      900: '#78350F',
    },
    // Blue - Secondary brand color
    blue: {
      50: '#EFF6FF',
      100: '#DBEAFE',
      200: '#BFDBFE',
      300: '#93C5FD',
      400: '#60A5FA',
      500: '#3B82F6',
      600: '#2563EB',  // Main blue
      700: '#1D4ED8',
      800: '#1E40AF',
      900: '#1E3A8A',
      950: '#172554',
    },
    // Dark backgrounds
    dark: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',  // Card background
      900: '#0F172A',  // Main background
      950: '#020617',  // Darkest
    },
  },

  // Gradient combinations
  gradients: {
    goldShine: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 50%, #F59E0B 100%)',
    goldDark: 'linear-gradient(135deg, #B45309 0%, #F59E0B 100%)',
    blueDark: 'linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%)',
    darkCard: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)',
    hero: 'linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0F172A 100%)',
    heroGold: 'linear-gradient(135deg, #0F172A 0%, #78350F 100%)',
  },

  // Semantic colors
  semantic: {
    success: '#10B981',
    error: '#EF4444',
    warning: '#F59E0B',
    info: '#3B82F6',
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
  textGold: 'text-amber-500',
  textBlue: 'text-blue-500',

  // Borders
  borderDefault: 'border-slate-700',
  borderGold: 'border-amber-500',
  borderBlue: 'border-blue-600',

  // Buttons
  btnPrimary: 'bg-amber-500 hover:bg-amber-600 text-slate-900 font-semibold',
  btnSecondary: 'bg-blue-600 hover:bg-blue-700 text-white',
  btnOutline: 'border-amber-500 text-amber-500 hover:bg-amber-500 hover:text-slate-900',
  btnGhost: 'text-slate-300 hover:text-white hover:bg-slate-700',

  // Cards
  card: 'bg-slate-800/50 border border-slate-700 rounded-xl',
  cardHover: 'hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-500/10',

  // Inputs
  input: 'bg-slate-800 border-slate-600 text-white placeholder:text-slate-400 focus:border-amber-500 focus:ring-amber-500/20',

  // Badges
  badgeGold: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  badgeBlue: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  badgeSuccess: 'bg-emerald-500/20 text-emerald-400',
  badgeDiscount: 'bg-red-500 text-white',
};

// CSS Variables for global styles
export const cssVariables = `
  :root {
    --color-gold: #F59E0B;
    --color-gold-light: #FBBF24;
    --color-gold-dark: #B45309;
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
