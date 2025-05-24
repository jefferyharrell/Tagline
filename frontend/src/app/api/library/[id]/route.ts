import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(`${backendUrl}/v1/media/${id}`, {
      headers: {
        Authorization: `Bearer ${authToken.value}`,
        "X-API-Key": backendApiKey || "",
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || "Failed to fetch media object" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching media object:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;
    const body = await request.json();

    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(`${backendUrl}/v1/media/${id}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${authToken.value}`,
        "X-API-Key": backendApiKey || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || "Failed to update media object" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("API Route PATCH - Error updating media object:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
