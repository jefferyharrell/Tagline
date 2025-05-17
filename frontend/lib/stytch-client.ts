"use client";

import { createStytchUIClient } from "@stytch/nextjs/ui";

export const stytchClient = createStytchUIClient(
  process.env.NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN || "",
);
