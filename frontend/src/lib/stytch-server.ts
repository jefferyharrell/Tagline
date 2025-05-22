import * as stytch from 'stytch';

let stytchClient: stytch.Client | null = null;

export function loadStytch(): stytch.Client {
  if (!stytchClient) {
    // Use the exact environment variable names from .env file
    stytchClient = new stytch.Client({
      project_id: process.env.STYTCH_PROJECT_ID || '',
      secret: process.env.STYTCH_SECRET || '',
      env: process.env.NODE_ENV === 'production' 
        ? stytch.envs.live 
        : stytch.envs.test,
    });
    
  }

  return stytchClient;
}
