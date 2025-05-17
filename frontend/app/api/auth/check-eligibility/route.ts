import { NextResponse } from "next/server";

// This would typically check against your user database or whitelist
// For now, we'll just allow any @example.com email for testing
const isEmailAllowed = (email: string): boolean => {
  // TODO: Replace with actual whitelist check
  return email.endsWith("@example.com") || email === "jefferyharrell@gmail.com";
};

export async function POST(request: Request) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json(
        { message: "Email is required" },
        { status: 400 },
      );
    }

    const isEligible = isEmailAllowed(email);

    if (!isEligible) {
      return NextResponse.json(
        {
          isEligible: false,
          message:
            "Access denied. Please contact support if you believe this is an error.",
        },
        { status: 403 },
      );
    }

    return NextResponse.json({
      isEligible: true,
      message: "Email is eligible for access",
    });
  } catch (error) {
    console.error("Error checking eligibility:", error);
    return NextResponse.json(
      {
        isEligible: false,
        message: "An error occurred while checking eligibility",
      },
      { status: 500 },
    );
  }
}
