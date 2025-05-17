export type UserRole = 'member' | 'admin' | 'active' | 'sustainer';

export interface User {
  id: string;
  email: string;
  roles: UserRole[];
  firstName?: string;
  lastName?: string;
  createdAt: string;
  lastLoginAt?: string;
}

export interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error: string | null;
}

export interface AuthContextType extends AuthState {
  login: (email: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkEligibility: (email: string) => Promise<boolean>;
  setState: (state: AuthState) => void;
}

export interface JWTPayload {
  sub: string;
  email: string;
  roles: UserRole[];
  iat: number;
  exp: number;
}
