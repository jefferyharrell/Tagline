'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { buttonVariants } from "@/components/ui/button"

interface PageHeaderProps {
  title: string;
}

export default function PageHeader({ title }: PageHeaderProps) {
  const pathname = usePathname();

  const isActive = (path: string) => {
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  return (
    <header className="bg-white shadow">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex justify-between items-center">
        <div className="flex items-center">
          <div className="h-10 w-auto mr-4">
            <Image 
              src="/JLLA.png" 
              alt="Junior League of Los Angeles" 
              width={200}
              height={200}
              priority={true}
              className="h-full w-auto object-contain"
            />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">{title}</h1>
        </div>
        <nav className="flex space-x-4">
          <Link 
            href="/dashboard"
            className={`${isActive('/dashboard') ? buttonVariants({ variant: "default" }) : buttonVariants({ variant: "secondary" })}`}
          >
            Dashboard
          </Link>
          <Link 
            href="/media" 
            className={`${isActive('/media') ? buttonVariants({ variant: "default" }) : buttonVariants({ variant: "secondary" })}`}
          >
            Media
          </Link>
        </nav>
      </div>
    </header>
  );
}
