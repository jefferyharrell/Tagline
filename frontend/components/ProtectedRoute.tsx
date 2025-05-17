"use client";

import { useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: string[];
}

export default function ProtectedRoute({
  children,
  requiredRoles = [],
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }

    if (
      !loading &&
      user &&
      requiredRoles.length > 0 &&
      !requiredRoles.some((role) => user.roles.includes(role))
    ) {
      router.push("/unauthorized");
    }
  }, [user, loading, router, requiredRoles]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return null; // Will redirect in useEffect
  }

  if (
    requiredRoles.length > 0 &&
    !requiredRoles.some((role) => user.roles.includes(role))
  ) {
    return null; // Will redirect in useEffect
  }

  return <>{children}</>;
}
