'use client';

import { Turnstile as TurnstileWidget, TurnstileInstance } from '@marsidev/react-turnstile';
import { useRef, forwardRef, useImperativeHandle } from 'react';

export interface TurnstileRef {
  reset: () => void;
  getResponse: () => string | undefined;
}

interface TurnstileProps {
  onSuccess: (token: string) => void;
  onError?: () => void;
  onExpire?: () => void;
  className?: string;
}

/**
 * Cloudflare Turnstile CAPTCHA component
 *
 * Usage:
 * 1. Get site key from Cloudflare Turnstile dashboard
 * 2. Set NEXT_PUBLIC_TURNSTILE_SITE_KEY in .env
 * 3. Use this component in forms that need bot protection
 *
 * For testing, use these keys:
 * - Always passes: 1x00000000000000000000AA
 * - Always fails: 2x00000000000000000000AB
 * - Forces interactive challenge: 3x00000000000000000000FF
 */
const Turnstile = forwardRef<TurnstileRef, TurnstileProps>(
  ({ onSuccess, onError, onExpire, className }, ref) => {
    const turnstileRef = useRef<TurnstileInstance>(null);

    const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

    useImperativeHandle(ref, () => ({
      reset: () => {
        turnstileRef.current?.reset();
      },
      getResponse: () => {
        return turnstileRef.current?.getResponse();
      },
    }));

    // If no site key configured, skip CAPTCHA (for development)
    if (!siteKey) {
      console.warn('Turnstile: NEXT_PUBLIC_TURNSTILE_SITE_KEY not configured, CAPTCHA disabled');
      // Auto-call onSuccess with empty token for development
      if (typeof window !== 'undefined') {
        setTimeout(() => onSuccess('development-bypass'), 100);
      }
      return null;
    }

    return (
      <div className={className}>
        <TurnstileWidget
          ref={turnstileRef}
          siteKey={siteKey}
          onSuccess={onSuccess}
          onError={onError}
          onExpire={onExpire}
          options={{
            theme: 'light',
            size: 'normal',
          }}
        />
      </div>
    );
  }
);

Turnstile.displayName = 'Turnstile';

export { Turnstile };
