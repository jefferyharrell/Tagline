import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LibraryView from "@/components/LibraryView";
import { verifyJwtToken } from "@/lib/jwt-utils";

interface LibraryFolderProps {
  params: Promise<{
    path: string[];
  }>;
}

export default async function LibraryFolder({ params }: LibraryFolderProps) {
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

  // Await params in Next.js 15
  const resolvedParams = await params;

  // Convert path array to string for the library view
  const pathString = resolvedParams.path.join("/");

  return <LibraryView initialPath={pathString} />;
}