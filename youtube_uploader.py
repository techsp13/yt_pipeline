"""
YouTube Data API v3 Direct Uploader Module

Uploads approved Short videos directly to your YouTube channel.
"""

import os
import sys
import json
import time

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "youtube_token.json")


def get_authenticated_service():
    """Authenticate and return YouTube API service."""
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"client_secrets.json not found at {CLIENT_SECRETS_FILE}."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            try:
                creds = flow.run_local_server(port=0, open_browser=True, timeout=180)
            except Exception as e:
                print(f"[OAuth Local Server Error]: {e}")
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"\n🔐 Please authorize YouTube Channel by opening this URL:\n{auth_url}\n")
                creds = flow.run_console()

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_short_to_youtube(video_path, title, description, tags=None, privacy_status="public"):
    """
    Uploads a video short directly to YouTube Channel.
    """
    if not os.path.exists(video_path):
        print(f"[YouTube Upload Error] Video file not found: {video_path}")
        return None

    try:
        from googleapiclient.http import MediaFileUpload

        youtube = get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags or ["Shorts", "AmazonFinds"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        print(f"🚀 Uploading '{title[:40]}...' directly to YouTube...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        print(f"✅ YouTube Upload Complete! Short URL: {video_url}")
        return video_url

    except Exception as e:
        print(f"[YouTube Upload Failed]: {e}")
        return None
