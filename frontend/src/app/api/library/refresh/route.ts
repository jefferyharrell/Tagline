import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(request: NextRequest) {
  try {
    // Get the auth token from cookies
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token");

    if (!authToken) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse request body
    const body = await request.json();
    const { path } = body;
    
    // Call the backend API to refresh the folder
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendApiKey = process.env.BACKEND_API_KEY;

    // First, call the library endpoint with refresh=true to clear cache
    const libraryUrl = new URL(`${backendUrl}/v1/library${path ? `/${path}` : ""}`);
    libraryUrl.searchParams.set("refresh", "true");
    libraryUrl.searchParams.set("limit", "1"); // Just need to trigger the refresh

    const libraryResponse = await fetch(libraryUrl.toString(), {
      headers: {
        Authorization: `Bearer ${authToken.value}`,
        "X-API-Key": backendApiKey || "",
      },
    });

    if (!libraryResponse.ok) {
      const error = await libraryResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || "Failed to refresh library data" },
        { status: libraryResponse.status },
      );
    }

    // Then trigger re-ingestion for this path with metadata preservation
    const ingestUrl = new URL(`${backendUrl}/v1/storage/ingest`);
    const ingestResponse = await fetch(ingestUrl.toString(), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${authToken.value}`,
        "X-API-Key": backendApiKey || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        path: path || "",
        preserve_metadata: true, // Don't overwrite existing metadata
        force_regenerate: true,  // Force regeneration of proxies/thumbnails
      }),
    });

    if (!ingestResponse.ok) {
      const error = await ingestResponse.json().catch(() => ({}));
      console.error("Failed to trigger ingest:", error);
      // Don't fail the whole operation if ingest fails
    }

    return NextResponse.json({ 
      success: true, 
      message: "Folder refresh initiated" 
    });
  } catch (error) {
    console.error("Error refreshing library data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}