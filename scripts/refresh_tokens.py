"""Refresh long-lived Instagram and Threads tokens."""

import asyncio
import sys
from pathlib import Path

# Ensure root directory is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import (
    is_facebook_connected,
    is_instagram_connected,
    is_threads_connected,
    refresh_instagram_token,
    refresh_threads_token,
)


async def main() -> None:
    print("=== Social Media Token Refresh ===")
    
    if is_instagram_connected():
        print("\nRefreshing Instagram token...")
        ig_res = await refresh_instagram_token()
        if ig_res.get("ok"):
            expires_days = ig_res.get("expires_in", 0) // 86400
            print(f"✅ Instagram token refreshed successfully. Valid for ~{expires_days} days.")
        else:
            print(f"❌ Instagram refresh failed: {ig_res.get('error')}")
    else:
        print("\nℹ️ Instagram: Not connected.")

    if is_threads_connected():
        print("\nRefreshing Threads token...")
        th_res = await refresh_threads_token()
        if th_res.get("ok"):
            expires_days = th_res.get("expires_in", 0) // 86400
            print(f"✅ Threads token refreshed successfully. Valid for ~{expires_days} days.")
        else:
            print(f"❌ Threads refresh failed: {th_res.get('error')}")
    else:
        print("\nℹ️ Threads: Not connected.")

    if is_facebook_connected():
        print("\nℹ️ Facebook Page: Connected (Page access tokens obtained with long-lived user tokens do not expire).")
    else:
        print("\nℹ️ Facebook Page: Not connected.")


if __name__ == "__main__":
    asyncio.run(main())
