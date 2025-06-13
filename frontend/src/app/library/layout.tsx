import { SidebarProvider } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";

export default function LibraryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <LibrarySidebar />
      <main className="flex-1 bg-gray-50">
        {children}
      </main>
    </SidebarProvider>
  );
}