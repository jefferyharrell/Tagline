'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { buttonVariants } from "@/components/ui/button"

interface PageHeaderProps {
  title: string;
  showSearch?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
}

export default function PageHeader({ 
  title, 
  showSearch = true, 
  searchValue = '', 
  onSearchChange,
  searchPlaceholder = 'Search media...'
}: PageHeaderProps) {
  const pathname = usePathname();

  const isActive = (path: string) => {
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  return (
    <header className="bg-white shadow">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex items-center justify-between">
        {/* Left: Logo and Title */}
        <div className="flex items-center flex-shrink-0">
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
          {title && <h1 className="text-3xl font-bold tracking-tight text-gray-900">{title}</h1>}
        </div>

        {/* Center: Search (if enabled) */}
        {showSearch && (
          <div className="flex-1 max-w-lg mx-8">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg 
                  className="h-5 w-5 text-gray-400" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
                  />
                </svg>
              </div>
              <input
                type="text"
                value={searchValue}
                onChange={(e) => onSearchChange?.(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder={searchPlaceholder}
              />
            </div>
          </div>
        )}

        {/* Right: Navigation */}
        <nav className="flex space-x-4 flex-shrink-0">
          <Link 
            href="/media" 
            className={`${isActive('/media') ? buttonVariants({ variant: "default" }) : buttonVariants({ variant: "secondary" })}`}
          >
            Media
          </Link>
          <Link 
            href="/dashboard"
            className={`${isActive('/dashboard') ? buttonVariants({ variant: "default" }) : buttonVariants({ variant: "secondary" })}`}
          >
            Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}
