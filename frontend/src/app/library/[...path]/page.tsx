import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LibraryClient from "../library-client";

interface LibraryFolderProps {
  params: Promise<{
    path: string[];
  }>;
}

export default async function LibraryFolder({ params }: LibraryFolderProps) {
  // Check if the user is authenticated
  const cookieStore = await cookies();
  const authToken = cookieStore.get("auth_token");

  if (!authToken) {
    redirect("/");
  }

  // Await params in Next.js 15
  const resolvedParams = await params;

  // Convert path array to string for the library client
  const pathString = resolvedParams.path.join("/");

  return <LibraryClient initialPath={pathString} />;
}