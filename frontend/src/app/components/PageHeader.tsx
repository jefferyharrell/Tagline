'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

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
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">{title}</h1>
        <nav className="flex space-x-4">
          <Link 
            href="/dashboard" 
            className={`${isActive('/dashboard') ? 'text-indigo-600 font-medium' : 'text-gray-600 hover:text-gray-900'}`}
          >
            Dashboard
          </Link>
          <Link 
            href="/media" 
            className={`${isActive('/media') ? 'text-indigo-600 font-medium' : 'text-gray-600 hover:text-gray-900'}`}
          >
            Media
          </Link>
        </nav>
      </div>
    </header>
  );
}
