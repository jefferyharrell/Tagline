import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ object_key: string }> },
) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { object_key } = await params;
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    const response = await fetch(
      `${backendUrl}/v1/media/${encodeURIComponent(object_key)}/thumbnail`,
      {
        headers: {
          Authorization: `Bearer ${authToken.value}`,
          "X-API-Key": backendApiKey || "",
        },
      },
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || "Failed to fetch thumbnail" },
        { status: response.status },
      );
    }

    // Get the thumbnail data as an array buffer
    const thumbnailBuffer = await response.arrayBuffer();
    const contentType = response.headers.get("content-type") || "image/jpeg";

    // Generate a simple ETag based on the object key
    const etag = `"${object_key}-thumbnail"`;

    // Check if client has a cached version
    const ifNoneMatch = request.headers.get("if-none-match");
    if (ifNoneMatch === etag) {
      return new NextResponse(null, { status: 304 });
    }

    // Return the thumbnail as a response with the proper content type
    return new NextResponse(thumbnailBuffer, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=31536000, immutable", // Cache for 1 year
        ETag: etag,
      },
    });
  } catch (error) {
    console.error("Error fetching thumbnail:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
