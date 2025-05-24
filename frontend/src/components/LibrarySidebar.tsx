"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

interface SidebarItem {
  title: string;
  href?: string;
  isActive?: boolean;
}

export default function LibrarySidebar() {
  const pathname = usePathname();

  const sections: SidebarSection[] = [
    {
      title: "Library",
      items: [
        { title: "Photos", href: "/library", isActive: pathname === "/library" },
      ],
    },
    {
      title: "By League Year",
      items: [
        { title: "2025-2026", href: "#" },
        { title: "2024-2025", href: "#" },
        { title: "2023-2024", href: "#" },
        { title: "2022-2023", href: "#" },
        { title: "2021-2022", href: "#" },
      ],
    },
    {
      title: "Me",
      items: [
        { title: "Dashboard", href: "/dashboard", isActive: pathname === "/dashboard" },
      ],
    },
  ];

  return (
    <div className="w-64 bg-gray-800 text-white h-full flex flex-col">
      <div className="flex-1 py-4 px-3 space-y-6">
        {sections.map((section, sectionIndex) => (
          <div key={sectionIndex}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-3">
              {section.title}
            </h3>
            <ul className="space-y-1">
              {section.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  {item.href && item.href !== "#" ? (
                    <Link
                      href={item.href}
                      className={`block px-3 py-2 text-sm rounded-md transition-colors duration-200 ${
                        item.isActive
                          ? "bg-gray-700 text-white"
                          : "text-gray-300 hover:bg-gray-700 hover:text-white"
                      }`}
                    >
                      {item.title}
                    </Link>
                  ) : (
                    <div className="block px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white rounded-md transition-colors duration-200 cursor-pointer">
                      {item.title}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}