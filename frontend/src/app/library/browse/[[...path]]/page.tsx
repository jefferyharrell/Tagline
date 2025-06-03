import BrowseClient from "./browse-client";

interface BrowsePageProps {
  params: Promise<{
    path?: string[];
  }>;
}

export default async function BrowsePage({ params }: BrowsePageProps) {
  // Await params in Next.js 15
  const resolvedParams = await params;

  // Convert path array to string, or use empty string for root
  const pathString = resolvedParams.path ? resolvedParams.path.join("/") : "";

  return <BrowseClient initialPath={pathString} />;
}
