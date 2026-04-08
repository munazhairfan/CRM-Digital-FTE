import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("Loading token...")
creds = Credentials.from_authorized_user_file("token.json")
print(f"Token valid: {creds.valid}")

print("Connecting to Gmail API...")
import urllib3
urllib3.disable_warnings()
service = build("gmail", "v1", credentials=creds, cache_discovery=False)

import socket
socket.setdefaulttimeout(10)

print("Fetching profile...")
try:
    profile = service.users().getProfile(userId="me").execute()
    print(f"✅ Gmail API connected!")
    print(f"   Email: {profile['emailAddress']}")
    print(f"   Total messages: {profile['messagesTotal']}")
except Exception as e:
    print(f"❌ Error: {e}")
