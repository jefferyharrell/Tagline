"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Images, Search, Users, RefreshCw } from "lucide-react";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { UserAvatar } from "@/components/user-avatar";
import { useUser } from "@/contexts/user-context";

interface SidebarItem {
  title: string;
  href: string;
  isActive: boolean;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

export default function LibrarySidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  
  // Check if user is an administrator
  const isAdmin = user?.roles?.some(role => role.name === 'administrator') ?? false;

  const items: SidebarItem[] = [
    {
      title: "Library",
      href: "/library",
      isActive: pathname === "/library" || pathname.startsWith("/library/"),
      icon: Images,
    },
    {
      title: "Search",
      href: "/search",
      isActive: pathname === "/search",
      icon: Search,
    },
    {
      title: "User Management",
      href: "/admin/users",
      isActive: pathname === "/admin/users",
      icon: Users,
      adminOnly: true,
    },
    {
      title: "Media Sync",
      href: "/admin/media-sync",
      isActive: pathname === "/admin/media-sync",
      icon: RefreshCw,
      adminOnly: true,
    },
  ];

  // Filter items based on admin status
  const visibleItems = items.filter(item => !item.adminOnly || isAdmin);

  return (
    <Sidebar collapsible="offcanvas" variant="inset">
      <SidebarHeader>
        <Link href="/library">
          <Image
            src="/JLLA_combo_stacked.svg"
            alt="Junior League of Los Angeles"
            width={1024}
            height={156}
            priority={true}
            className="object-contain p-2"
          />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {visibleItems.map((item, index) => (
                <SidebarMenuItem key={index}>
                  <SidebarMenuButton asChild isActive={item.isActive}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="pb-4">
        <UserAvatar />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
