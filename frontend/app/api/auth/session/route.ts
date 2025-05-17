import { NextResponse } from "next/server";
import { loadStytch } from "@/lib/stytch-server";

export async function POST(request: Request) {
  const data = await request.json();
  const { token } = data;

  try {
    // Authenticate with Stytch
    const stytch = loadStytch();
    const authResponse = await stytch.magicLinks.authenticate({ token });

    // Verify with our backend and get user roles
    const backendResponse = await fetch(
      `${process.env.API_URL}/v1/auth/authenticate`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.API_KEY || "",
        },
        body: JSON.stringify({ token }),
      },
    );

    const backendResult = await backendResponse.json();

    // Combine Stytch session with our backend user data
    return NextResponse.json({
      sessionToken: authResponse.session_token,
      sessionJwt: backendResult.access_token,
      userRoles: backendResult.user_roles,
    });
  } catch (error) {
    console.error("Authentication error:", error);
    return NextResponse.json(
      { error: "Authentication failed" },
      { status: 401 },
    );
  }
}
