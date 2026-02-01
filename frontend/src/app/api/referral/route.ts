import { NextRequest, NextResponse } from 'next/server';

const REFERRAL_COOKIE_NAME = 'partner_ref';

/**
 * GET /api/referral
 * Returns the partner referral code from the httpOnly cookie
 * This allows the checkout page to get the referral code securely
 */
export async function GET(request: NextRequest) {
  const refCode = request.cookies.get(REFERRAL_COOKIE_NAME)?.value || null;

  return NextResponse.json({
    partner_code: refCode,
  });
}

/**
 * DELETE /api/referral
 * Clears the partner referral cookie (after successful order)
 */
export async function DELETE() {
  const response = NextResponse.json({ success: true });

  // Clear the cookie by setting it to expire in the past
  response.cookies.set(REFERRAL_COOKIE_NAME, '', {
    maxAge: 0,
    path: '/',
  });

  return response;
}
