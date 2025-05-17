export type UserRole = "member" | "admin" | "active" | "sustainer";

export interface User {
  id: string;
  email: string;
  name?: string;
  roles: UserRole[];
  // Add other user fields as needed
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
  hasRole: (role: UserRole) => boolean;
  hasAnyRole: (roles: UserRole[]) => boolean;
};
