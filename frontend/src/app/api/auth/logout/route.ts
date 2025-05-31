import { NextResponse } from 'next/server';
import { clearAuthCookie } from '@/lib/jwt-utils';

export async function POST() {
  try {
    // Clear the auth cookie
    await clearAuthCookie();
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json(
      { error: 'Failed to logout' },
      { status: 500 }
    );
  }
}