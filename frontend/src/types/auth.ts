export type UserRole = 'member' | 'admin' | 'active' | 'sustainer';

export interface UserMetadata {
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
}

export interface User {
  id: string;
  email: string;
  name?: string;
  roles: UserRole[];
  metadata: UserMetadata;
  isEmailVerified: boolean;
  stytchUserId?: string;
}

// JWT Payload from our backend
export interface JwtPayload {
  sub: string; // user ID
  email: string;
  roles: UserRole[];
  iat: number; // issued at
  exp: number; // expiration time
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  success: boolean;
}

export interface LoginResponse {
  user: User;
  token: string;
  refreshToken?: string;
}

export interface CheckEligibilityResponse {
  isEligible: boolean;
  message?: string;
  userExists: boolean;
}

// Error Types
export class AuthError extends Error {
  code: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    code: string = 'AUTH_ERROR',
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AuthError';
    this.code = code;
    this.details = details;
  }
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    status: number = 500,
    code: string = 'API_ERROR',
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
  hasRole: (role: UserRole) => boolean;
  hasAnyRole: (roles: UserRole[]) => boolean;
  refreshToken: () => Promise<boolean>;
};
