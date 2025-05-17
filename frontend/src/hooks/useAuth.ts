import { useCallback } from "react";
import { useAuth as useAuthContext } from "@/contexts/AuthContext";
import { UserRole } from "@/types/auth";

export const useAuth = () => {
  const context = useAuthContext();

  // Add memoized role checkers
  const hasRole = useCallback(
    (role: UserRole) => context.hasRole(role),
    [context],
  );

  const hasAnyRole = useCallback(
    (roles: UserRole[]) => context.hasAnyRole(roles),
    [context],
  );

  return {
    ...context,
    hasRole,
    hasAnyRole,
  };
};
