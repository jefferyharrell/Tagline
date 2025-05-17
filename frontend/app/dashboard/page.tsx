"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute requiredRoles={["member"]}>
      <div className="dashboard p-8">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

        <div className="user-info bg-white p-6 rounded-lg shadow-md mb-6">
          <p className="mb-2">Welcome, {user?.email}</p>
          <p className="mb-4">Roles: {user?.roles.join(", ")}</p>

          <button
            onClick={logout}
            className="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Log Out
          </button>
        </div>

        {user?.roles.includes("admin") && (
          <div className="admin-panel bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Admin Panel</h2>
            <p>This section is only visible to administrators.</p>
            {/* Admin-specific functionality here */}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
