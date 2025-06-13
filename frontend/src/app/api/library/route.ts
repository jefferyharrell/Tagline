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

    // Extract parameters from URL
    const { searchParams } = new URL(request.url);
    const path = searchParams.get("path");
    const limit = searchParams.get("limit") || "36";
    const offset = searchParams.get("offset") || "0";
    const refresh = searchParams.get("refresh");
    
    // Call the backend API for library browsing
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    // Build URL - use the new library endpoint
    const url = new URL(`${backendUrl}/v1/library${path ? `/${path}` : ""}`);
    url.searchParams.set("limit", limit);
    url.searchParams.set("offset", offset);
    if (refresh === "true") {
      url.searchParams.set("refresh", "true");
    }

    const response = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${authToken.value}`,
        "X-API-Key": backendApiKey || "",
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || "Failed to fetch library data" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching library data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
