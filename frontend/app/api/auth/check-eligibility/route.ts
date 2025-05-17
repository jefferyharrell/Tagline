import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const data = await request.json();

  try {
    const response = await fetch(
      `${process.env.API_URL}/v1/auth/verify-email`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.API_KEY || "",
        },
        body: JSON.stringify({ email: data.email }),
      },
    );

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error checking email eligibility:", error);
    return NextResponse.json(
      { error: "Failed to check email eligibility" },
      { status: 500 },
    );
  }
}
