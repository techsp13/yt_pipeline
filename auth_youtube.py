"""
1-Time YouTube Channel Authorization Script

Run this once in terminal to authorize your YouTube Channel.
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "youtube_token.json")


def main():
    print("=" * 60)
    print("  YOUTUBE CHANNEL 1-TIME AUTHORIZATION")
    print("=" * 60)

    if not os.path.exists(CLIENT_SECRETS):
        print(f"Error: client_secrets.json not found at {CLIENT_SECRETS}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
    
    print("\nStarting local authentication server...")
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())

    print("\n✅ YouTube Token Saved Successfully to youtube_token.json!")


if __name__ == "__main__":
    main()
