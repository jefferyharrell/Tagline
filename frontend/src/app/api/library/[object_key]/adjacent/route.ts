import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ object_key: string }> },
) {
  const { object_key } = await params;
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const backendApiKey = process.env.BACKEND_API_KEY;

  try {
    const response = await fetch(
      `${backendUrl}/v1/media/${encodeURIComponent(object_key)}/adjacent`,
      {
        headers: {
          Authorization: `Bearer ${authToken.value}`,
          "X-API-Key": backendApiKey || "",
        },
      },
    );

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || "Failed to fetch adjacent media" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching adjacent media:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
