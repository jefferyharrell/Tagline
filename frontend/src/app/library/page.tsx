import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LibraryView from "@/components/LibraryView";
import { verifyJwtToken } from "@/lib/jwt-utils";

export default async function Library() {
  // Check if the user is authenticated with a valid token
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken?.value) {
    redirect("/");
  }

  // Verify the JWT token is valid
  const payload = await verifyJwtToken(authToken.value);
  if (!payload) {
    redirect("/");
  }

  // Show the library browser directly at root
  return <LibraryView initialPath="" />;
}
