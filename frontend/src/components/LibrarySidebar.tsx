"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Images,
  Calendar,
  LayoutDashboard,
} from "lucide-react";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { UserAvatar } from "@/components/user-avatar";

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

interface SidebarItem {
  title: string;
  href?: string;
  isActive?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
}

export default function LibrarySidebar() {
  const pathname = usePathname();

  const sections: SidebarSection[] = [
    {
      title: "Library",
      items: [
        { title: "Photos", href: "/library", isActive: pathname === "/library", icon: Images },
      ],
    },
    {
      title: "By League Year",
      items: [
        { title: "2025-2026", href: "#", icon: Calendar },
        { title: "2024-2025", href: "#", icon: Calendar },
        { title: "2023-2024", href: "#", icon: Calendar },
        { title: "2022-2023", href: "#", icon: Calendar },
        { title: "2021-2022", href: "#", icon: Calendar },
      ],
    },
    {
      title: "Me",
      items: [
        { title: "Dashboard", href: "/dashboard", isActive: pathname === "/dashboard", icon: LayoutDashboard },
      ],
    },
  ];

  return (
    <Sidebar collapsible="offcanvas">
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
        {sections.map((section, sectionIndex) => (
          <SidebarGroup key={sectionIndex}>
            <SidebarGroupLabel>{section.title}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item, itemIndex) => (
                  <SidebarMenuItem key={itemIndex}>
                    {item.href && item.href !== "#" ? (
                      <SidebarMenuButton asChild isActive={item.isActive}>
                        <Link href={item.href}>
                          {item.icon && <item.icon />}
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    ) : (
                      <SidebarMenuButton disabled>
                        {item.icon && <item.icon />}
                        <span>{item.title}</span>
                      </SidebarMenuButton>
                    )}
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <UserAvatar />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}