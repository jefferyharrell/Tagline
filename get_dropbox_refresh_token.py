#!/usr/bin/env python3
"""
Tagline Dropbox Onboarding Script

Guides you through generating a Dropbox OAuth2 refresh token for use with the Tagline backend.
Run this inside your backend container or anywhere with Python 3.7+ and the 'requests' library installed.

Features:
- Friendly, step-by-step prompts
- Opens browser for Dropbox OAuth2 flow (or gives you a URL)
- Handles errors and explains what to do if something goes wrong
- Prints a ready-to-paste .env snippet at the end
"""
import sys
import webbrowser
from urllib.parse import urlencode

import requests

DEFAULT_SCOPES = [
    "account_info.read",
    "files.metadata.read",
    "files.content.read",
]
AUTHORIZE_URL = "https://www.dropbox.com/oauth2/authorize"
TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"


def prompt(msg, secret=False):
    try:
        if secret:
            import getpass

            return getpass.getpass(msg)
        return input(msg)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(1)


def main():
    print("\n=== Tagline Dropbox Onboarding ===\n")
    print(
        "This script will help you generate a Dropbox OAuth2 refresh token for Tagline.\n"
    )

    app_key = prompt("Dropbox App Key: ")
    app_secret = prompt("Dropbox App Secret: ", secret=True)
    default_scope_str = " ".join(DEFAULT_SCOPES)
    scope = (
        prompt(f"Dropbox OAuth2 scopes [{default_scope_str}]: ") or default_scope_str
    )

    # Step 1: Build the authorization URL
    params = {
        "client_id": app_key,
        "token_access_type": "offline",  # Required for refresh token
        "response_type": "code",
        "scope": scope,
    }
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"

    print("\n1. Open this URL in your browser and authorize the app:")
    print(f"   {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass  # It's fine if this fails

    # Step 2: User pastes the code
    code = prompt("2. Paste the authorization code here: ")
    print("\nExchanging code for refresh token...")

    # Step 3: Exchange code for refresh token
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": app_key,
        "client_secret": app_secret,
    }
    try:
        resp = requests.post(TOKEN_URL, data=data, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"\nERROR: Failed to exchange code for token: {e}\n")
        print("Check your App Key/Secret and try again.\n")
        sys.exit(1)

    token_data = resp.json()
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print(f"\nERROR: No refresh token found in response: {token_data}\n")
        sys.exit(1)

    print("\nSUCCESS! Here is your Dropbox refresh token:")
    print("=" * 60)
    print(f"DROPBOX_REFRESH_TOKEN={refresh_token}")
    print(f"DROPBOX_APP_KEY={app_key}")
    print(f"DROPBOX_APP_SECRET={app_secret}")
    print("=" * 60)
    print("\nPaste these into your .env file and restart Tagline.\n")
    print("You’re all set! 🎉\n")


if __name__ == "__main__":
    main()
