"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";

interface User {
  id: string;
  email: string;
  roles: string[];
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (
    sessionToken: string,
    sessionJwt: string,
    userRoles: string[],
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check if authentication is bypassed for development
    if (process.env.BYPASS_AUTH === "true") {
      setUser({
        id: "dev-user",
        email: "dev@example.com",
        roles: ["admin", "member"],
      });
      setLoading(false);
      return;
    }

    // Check if we have a session in localStorage
    const checkSession = async () => {
      try {
        const sessionJwt = localStorage.getItem("sessionJwt");

        if (sessionJwt) {
          // Verify JWT on the client side by parsing payload
          const payload = JSON.parse(atob(sessionJwt.split(".")[1]));

          if (payload && payload.roles) {
            setUser({
              id: payload.user_id,
              email: payload.email,
              roles: payload.roles,
            });
          }
        }
      } catch (error) {
        console.error("Error checking session:", error);
        // Clear potentially invalid session
        localStorage.removeItem("sessionJwt");
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (
    sessionToken: string,
    sessionJwt: string,
    userRoles: string[],
  ) => {
    localStorage.setItem("sessionJwt", sessionJwt);

    // Parse JWT payload to get user info
    const payload = JSON.parse(atob(sessionJwt.split(".")[1]));

    setUser({
      id: payload.user_id,
      email: payload.email,
      roles: userRoles,
    });

    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("sessionJwt");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
