import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function Library() {
  // Check if the user is authenticated
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  // Redirect to the browse route
  redirect("/library/browse");
}
