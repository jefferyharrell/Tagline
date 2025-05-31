'use client';

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUser, AUTH_STATE_CHANGE_EVENT } from "@/contexts/user-context";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

export function UserAvatar() {
  const { user, loading, clearUser } = useUser();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      // Clear user data immediately for better UX
      clearUser();
      
      // Clear the auth cookie
      await fetch('/api/auth/logout', { method: 'POST' });
      
      // Trigger auth state change event
      window.dispatchEvent(new Event(AUTH_STATE_CHANGE_EVENT));
      
      // Redirect to home page
      router.push('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex flex-col gap-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Generate initials from name or email
  const getInitials = () => {
    if (user.firstname && user.lastname) {
      return `${user.firstname[0]}${user.lastname[0]}`.toUpperCase();
    } else if (user.firstname) {
      return user.firstname.substring(0, 2).toUpperCase();
    } else if (user.lastname) {
      return user.lastname.substring(0, 2).toUpperCase();
    } else {
      // Use email if no name is available
      const emailParts = user.email.split('@')[0].split('.');
      if (emailParts.length >= 2) {
        return `${emailParts[0][0]}${emailParts[1][0]}`.toUpperCase();
      }
      return user.email.substring(0, 2).toUpperCase();
    }
  };

  // Display name logic
  const getDisplayName = () => {
    if (user.firstname || user.lastname) {
      return `${user.firstname || ''} ${user.lastname || ''}`.trim();
    }
    return user.email.split('@')[0];
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent transition-colors w-full text-left">
          <Avatar>
            <AvatarImage src={undefined} alt={getDisplayName()} />
            <AvatarFallback>{getInitials()}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium truncate">{getDisplayName()}</span>
            <span className="text-xs text-muted-foreground truncate">{user.email}</span>
          </div>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          <span>Logout</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}