import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';
import { SidebarProvider } from "@/components/ui/sidebar";
import LibrarySidebar from "@/components/LibrarySidebar";

interface JWTPayload {
  user_id: string;
  email: string;
  roles: string[];
}

function parseJwt(token: string): JWTPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Check if user has admin role
  const cookieStore = await cookies();
  const token = cookieStore.get('auth_token');

  if (!token) {
    redirect('/authenticate');
  }

  const payload = parseJwt(token.value);
  
  if (!payload || !payload.roles || !payload.roles.includes('administrator')) {
    // User doesn't have admin role
    redirect('/library');
  }

  return (
    <SidebarProvider>
      <LibrarySidebar />
      <main className="flex-1 bg-gray-50">
        {children}
      </main>
    </SidebarProvider>
  );
}