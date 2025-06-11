'use client';

import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSidebar } from '@/components/ui/sidebar';

interface MobilePageHeaderProps {
  title: string;
  className?: string;
}

export default function MobilePageHeader({ title, className = '' }: MobilePageHeaderProps) {
  const { toggleSidebar } = useSidebar();

  return (
    <div className={`md:hidden px-6 py-4 border-b border-gray-200 bg-white ${className}`}>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-3 p-3"
          onClick={toggleSidebar}
          aria-label="Toggle Sidebar"
        >
          <Menu style={{ width: '24px', height: '24px' }} />
        </Button>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
      </div>
    </div>
  );
}