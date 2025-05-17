import * as stytch from "stytch";

let stytchClient: stytch.Client | null = null;

export function loadStytch(): stytch.Client {
  if (!stytchClient) {
    stytchClient = new stytch.Client({
      project_id: process.env.NEXT_PUBLIC_STYTCH_PROJECT_ID || "",
      secret: process.env.STYTCH_SECRET_TOKEN || "",
      env:
        process.env.NEXT_PUBLIC_STYTCH_PROJECT_ENV === "live"
          ? stytch.envs.live
          : stytch.envs.test,
    });
  }

  return stytchClient;
}
