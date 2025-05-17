import { NextResponse } from "next/server";
import * as stytch from "stytch";

// Initialize Stytch client
const stytchClient = new stytch.Client({
  project_id: process.env.STYTCH_PROJECT_ID || "",
  secret: process.env.STYTCH_SECRET_TOKEN || "",
  env:
    process.env.NODE_ENV === "production" ? stytch.envs.live : stytch.envs.test,
});

export async function POST(request: Request) {
  try {
    const { token } = await request.json();

    if (!token) {
      return NextResponse.json(
        { message: "Token is required" },
        { status: 400 },
      );
    }

    // Authenticate the magic link token with Stytch
    const stytchResponse = await stytchClient.magicLinks.authenticate({
      magic_links_token: token,
      session_duration_minutes: 60 * 24 * 7, // 7 days
    });

    if (!stytchResponse.session_jwt || !stytchResponse.user_id) {
      throw new Error("Invalid session data from Stytch");
    }

    // Here you would typically:
    // 1. Look up or create the user in your database
    // 2. Generate a session token for your application
    // 3. Set any necessary cookies

    // For now, we'll return a simplified response
    return NextResponse.json({
      sessionToken: stytchResponse.session_jwt,
      user: {
        id: stytchResponse.user_id,
        email: stytchResponse.user?.emails?.[0]?.email || "unknown@example.com",
        // Add any other user fields you need
      },
      // In a real app, you might want to set an HTTP-only cookie here
    });
  } catch (error) {
    console.error("Session creation error:", error);

    // Handle specific Stytch errors
    if (error instanceof stytch.errors.StytchError) {
      if (error.error_type === "invalid_token") {
        return NextResponse.json(
          { message: "Invalid or expired token" },
          { status: 401 },
        );
      }
    }

    return NextResponse.json(
      { message: "Failed to create session" },
      { status: 500 },
    );
  }
}
