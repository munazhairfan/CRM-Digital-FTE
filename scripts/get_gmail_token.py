"""One-time OAuth script to get Gmail API token.json"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

# These scopes let us read emails and send replies
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

def main():
    creds_file = "credentials.json"
    token_file = "token.json"

    if not os.path.exists(creds_file):
        print(f"❌ {creds_file} not found. Put your OAuth client secret here first.")
        return

    print("🔐 Opening browser for Gmail OAuth...")
    print("   → Click 'Allow' when Google asks for permission.")
    print("   → Then come back here — the script will save token.json automatically.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the token
    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print()
    print(f"✅ token.json saved! You can now use the Gmail API.")
    print("   The file contains your refresh token and access token.")

if __name__ == "__main__":
    main()
