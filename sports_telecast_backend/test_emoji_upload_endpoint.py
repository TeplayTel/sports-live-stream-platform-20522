#!/usr/bin/env python3
"""
Simple test for the emoji upload endpoint to ensure Authorization header is accepted
and multipart/form-data payload with 'emojiImage' and 'emojiType' works.
"""
import os
import sys
import requests

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:3001")

def main():
    # Basic server check
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if r.status_code != 200:
            print(f"❌ Backend not healthy at {BASE_URL}: {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot reach backend at {BASE_URL}: {e}")
        sys.exit(1)

    token = os.getenv("ADMIN_UPLOAD_TOKEN", "admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Prepare a small fake PNG payload (content not validated by server)
    files = {
        "emojiImage": ("test.png", b"\x89PNG\r\n\x1a\n\x00\x00fakeimage", "image/png")
    }
    data = {
        "emojiType": "clap"
    }

    resp = requests.post(f"{BASE_URL}/fan-engagement/emoji/v1/upload", headers=headers, files=files, data=data)
    print("Status:", resp.status_code)
    print("Body:", resp.text)
    if resp.status_code != 200:
        print("❌ Upload test failed")
        sys.exit(1)
    try:
        j = resp.json()
        assert j.get("status") == "SUCCESS"
        assert "emoji" in j
        assert "emoji_id" in j["emoji"]
        assert "image_url" in j["emoji"]
    except Exception as e:
        print(f"❌ Upload response validation failed: {e}")
        sys.exit(1)
    print("✅ Upload endpoint works")
    sys.exit(0)

if __name__ == "__main__":
    main()
