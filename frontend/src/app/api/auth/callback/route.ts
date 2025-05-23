import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { token } = await request.json();

    if (!token) {
      return NextResponse.json(
        { message: "Missing authentication token" },
        { status: 400 },
      );
    }

    // Use fallback URL if BACKEND_URL is not set
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const apiKey = process.env.BACKEND_API_KEY || "";

    // Call backend directly with the token - backend will handle Stytch verification
    const backendResponse = await fetch(`${backendUrl}/v1/auth/authenticate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        token: token,
      }),
    });

    if (!backendResponse.ok) {
      let errorData;
      try {
        errorData = await backendResponse.json();
        console.error("Backend error details:", errorData);
      } catch {
        const textResponse = await backendResponse
          .text()
          .catch(() => "Could not read response text");
        console.error("Backend error response text:", textResponse);
        errorData = {
          message: `Error ${backendResponse.status}: ${textResponse}`,
        };
      }

      return NextResponse.json(
        {
          message:
            errorData.detail || errorData.message || "Authentication failed",
        },
        { status: backendResponse.status },
      );
    }

    const userResponse = await backendResponse.json();

    // Create response with JWT
    const response = NextResponse.json({
      success: true,
      token: userResponse.access_token,
      roles: userResponse.user_roles,
    });

    // Set JWT in HTTP-only cookie
    response.cookies.set({
      name: "auth_token",
      value: userResponse.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });

    return response;
  } catch (error) {
    console.error("Authentication error:", error);
    return NextResponse.json(
      {
        message:
          "Authentication failed: " +
          (error instanceof Error ? error.message : String(error)),
      },
      { status: 500 },
    );
  }
}
