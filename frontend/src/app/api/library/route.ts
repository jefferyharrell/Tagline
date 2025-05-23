import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(request: NextRequest) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Extract pagination parameters from URL
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "24", 10);
    const offset = parseInt(searchParams.get("offset") || "0", 10);

    // Call the backend API to get media objects with pagination
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(
      `${backendUrl}/v1/media?limit=${limit}&offset=${offset}`,
      {
        headers: {
          Authorization: `Bearer ${authToken.value}`,
          "X-API-Key": backendApiKey || "",
        },
      },
    );

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || "Failed to fetch media objects" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching media objects:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
