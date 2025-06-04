import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import LibraryView from "@/components/LibraryView";

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

  // Convert path array to string for the library view
  const pathString = resolvedParams.path.join("/");

  return <LibraryView initialPath={pathString} />;
}