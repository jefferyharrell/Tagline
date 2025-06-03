import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";

export default function LibraryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <LibrarySidebar />
      <SidebarInset className="min-h-screen bg-gray-50">
        {children}
      </SidebarInset>
    </SidebarProvider>
  );
}