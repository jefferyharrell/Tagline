import { NextResponse } from "next/server";
import { loadStytch } from "@/lib/stytch-server";

export async function POST(request: Request) {
  const data = await request.json();
  const { email } = data;

  try {
    // First check eligibility with our backend
    const eligibilityResponse = await fetch(
      `${process.env.API_URL}/v1/auth/verify-email-eligibility`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.API_KEY || "",
        },
        body: JSON.stringify({ email }),
      },
    );

    const eligibilityResult = await eligibilityResponse.json();

    if (!eligibilityResult.eligible) {
      return NextResponse.json(
        {
          success: false,
          error: "This email is not authorized to access the application.",
        },
        { status: 403 },
      );
    }

    // Send magic link via Stytch
    const stytch = loadStytch();
    await stytch.magicLinks.email.loginOrCreate({
      email,
      login_magic_link_url: `${process.env.NEXTAUTH_URL || window.location.origin}/auth/callback`,
      signup_magic_link_url: `${process.env.NEXTAUTH_URL || window.location.origin}/auth/callback`,
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error sending magic link:", error);
    return NextResponse.json(
      { success: false, error: "Failed to send magic link" },
      { status: 500 },
    );
  }
}
