import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookie } from "@/lib/jwt-utils";

export async function POST() {
  try {
    // Clear the auth cookie
    await clearAuthCookie();

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json({ error: "Failed to logout" }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    // Clear the auth cookie
    await clearAuthCookie();

    // Redirect to home page
    return NextResponse.redirect(new URL("/", request.url));
  } catch (error) {
    console.error("Logout error:", error);
    // Even if clearing fails, redirect to home
    return NextResponse.redirect(new URL("/", request.url));
  }
}
