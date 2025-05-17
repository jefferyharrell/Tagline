import React from "react";

interface LogoPlaceholderProps {
  className?: string;
}

export function LogoPlaceholder({ className = "" }: LogoPlaceholderProps) {
  return (
    <div
      className={`relative flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg ${className}`}
      style={{ width: "256px", height: "256px" }}
    >
      <div className="text-center p-4">
        <div className="text-2xl font-bold text-gray-500 dark:text-gray-400">
          JLLA
        </div>
        <div className="text-sm text-gray-400 dark:text-gray-500 mt-2">
          Logo Placeholder
        </div>
      </div>
    </div>
  );
}
