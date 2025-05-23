"use client";

import { StytchProvider as Stytch } from "@stytch/nextjs";
import { createStytchUIClient } from "@stytch/nextjs/ui";
import { ReactNode, useMemo } from "react";

interface StytchProviderProps {
  children: ReactNode;
}

export function StytchProvider({ children }: StytchProviderProps) {
  // Initialize the Stytch client with the public token using useMemo to prevent recreation on re-renders
  const stytch = useMemo(
    () => createStytchUIClient(process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN!),
    [], // Empty dependency array ensures this only runs once
  );

  return <Stytch stytch={stytch}>{children}</Stytch>;
}
