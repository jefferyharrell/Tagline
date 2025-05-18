"use client";

import { StytchProvider as Stytch } from "@stytch/nextjs";
import { createStytchUIClient } from "@stytch/nextjs/ui";
import { ReactNode } from "react";

interface StytchProviderProps {
  children: ReactNode;
}

export function StytchProvider({ children }: StytchProviderProps) {
  // Initialize the Stytch client with the public token
  const stytch = createStytchUIClient(
    process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN!,
  );

  return <Stytch stytch={stytch}>{children}</Stytch>;
}
