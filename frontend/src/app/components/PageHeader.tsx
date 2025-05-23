'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';

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
  searchPlaceholder = 'Search library...'
}: PageHeaderProps) {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const isActive = (path: string) => {
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

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

        {/* Right: Hamburger Menu */}
        <div className="relative flex-shrink-0" ref={menuRef}>
          <button
            onClick={toggleMenu}
            className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            aria-expanded={isMenuOpen}
            aria-haspopup="true"
          >
            <span className="sr-only">Open menu</span>
            <svg 
              className="h-6 w-6" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M4 6h16M4 12h16M4 18h16" 
              />
            </svg>
          </button>

          {/* Dropdown Menu */}
          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
              <div className="py-1" role="menu" aria-orientation="vertical">
                <Link 
                  href="/library" 
                  className={`block px-4 py-2 text-sm hover:bg-gray-100 ${
                    isActive('/library') ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700'
                  }`}
                  role="menuitem"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Library
                </Link>
                <Link 
                  href="/dashboard"
                  className={`block px-4 py-2 text-sm hover:bg-gray-100 ${
                    isActive('/dashboard') ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700'
                  }`}
                  role="menuitem"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Dashboard
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
