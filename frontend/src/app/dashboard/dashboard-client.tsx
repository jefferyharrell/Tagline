"use client";

import { useEffect } from "react";
import { toast } from "sonner";

interface DashboardClientProps {
  errorMessage?: string;
  successMessage?: string;
}

export default function DashboardClient({
  errorMessage,
  successMessage,
}: DashboardClientProps) {
  useEffect(() => {
    if (errorMessage) {
      toast.error(errorMessage);
    }
    if (successMessage) {
      toast.success(successMessage);
    }
  }, [errorMessage, successMessage]);

  return null; // This component only handles side effects
}