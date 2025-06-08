import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";

export default function SearchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <LibrarySidebar />
      <SidebarInset className="bg-gray-50">
        {children}
      </SidebarInset>
    </SidebarProvider>
  );
}