"""Unit and integration tests for photo automation backend."""

import asyncio
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.fernet import Fernet
from starlette.testclient import TestClient

# Generate a test Fernet key and environment variables
TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ["TOKEN_ENCRYPTION_KEY"] = TEST_FERNET_KEY
os.environ["SESSION_SECRET"] = "test-session-secret"
os.environ["TELEGRAM_BOT_TOKEN"] = "test-bot-token"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["AUTHORIZED_TELEGRAM_USER_ID"] = "123456789"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["PUBLIC_BASE_URL"] = "https://test.example.com"
os.environ["INSTAGRAM_APP_ID"] = "test-ig-id"
os.environ["INSTAGRAM_APP_SECRET"] = "test-ig-secret"
os.environ["INSTAGRAM_REDIRECT_URI"] = "https://test.example.com/auth/instagram/callback"
os.environ["FACEBOOK_APP_ID"] = "test-fb-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-fb-secret"
os.environ["FACEBOOK_REDIRECT_URI"] = "https://test.example.com/auth/facebook/callback"
os.environ["THREADS_APP_ID"] = "test-th-id"
os.environ["THREADS_APP_SECRET"] = "test-th-secret"
os.environ["THREADS_REDIRECT_URI"] = "https://test.example.com/auth/threads/callback"

import app.main as main
from app.main import app, fernet, save_encrypted, load_encrypted, database


class TestPhotoAutomation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.test_dir) / "data"
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        main.DATA_DIR = self.test_data_dir
        main.TOKEN_FILE = self.test_data_dir / "instagram_token.enc"
        main.FACEBOOK_TOKEN_FILE = self.test_data_dir / "facebook_page_token.enc"
        main.FACEBOOK_PENDING_FILE = self.test_data_dir / "facebook_pending_pages.enc"
        main.THREADS_TOKEN_FILE = self.test_data_dir / "threads_token.enc"
        main.DATABASE_FILE = self.test_data_dir / "posts.sqlite3"
        main.MEDIA_DIR = self.test_data_dir / "media"
        main.MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_health_and_ping(self):
        # Test ping
        resp = self.client.get("/ping")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

        # Test health
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["instagram_oauth_configured"])
        self.assertTrue(data["facebook_oauth_configured"])
        self.assertTrue(data["threads_oauth_configured"])
        self.assertTrue(data["telegram_workflow_configured"])

    def test_encryption_and_env_fallback(self):
        f = fernet()
        sample_token = {"access_token": "ig-secret-123", "user_id": "999"}
        
        # Save and load to file
        save_encrypted(main.TOKEN_FILE, sample_token)
        loaded = load_encrypted(main.TOKEN_FILE)
        self.assertEqual(loaded["access_token"], "ig-secret-123")

        # Test env var fallback when file does not exist
        main.TOKEN_FILE.unlink()
        enc_str = f.encrypt(json.dumps(sample_token).encode()).decode("ascii")
        with patch.dict(os.environ, {"INSTAGRAM_TOKEN_ENCRYPTED": enc_str}):
            self.assertTrue(main.is_instagram_connected())
            loaded_env = load_encrypted(main.TOKEN_FILE)
            self.assertEqual(loaded_env["access_token"], "ig-secret-123")

        # Test Facebook env fallback
        fb_sample = {"id": "fb-page-123", "access_token": "fb-token-456"}
        fb_enc_str = f.encrypt(json.dumps(fb_sample).encode()).decode("ascii")
        with patch.dict(os.environ, {"FACEBOOK_TOKEN_ENCRYPTED": fb_enc_str}):
            self.assertTrue(main.is_facebook_connected())
            loaded_fb = load_encrypted(main.FACEBOOK_TOKEN_FILE)
            self.assertEqual(loaded_fb["id"], "fb-page-123")

        # Test Threads env fallback
        th_sample = {"id": "th-user-123", "access_token": "th-token-456"}
        th_enc_str = f.encrypt(json.dumps(th_sample).encode()).decode("ascii")
        with patch.dict(os.environ, {"THREADS_TOKEN_ENCRYPTED": th_enc_str}):
            self.assertTrue(main.is_threads_connected())
            loaded_th = load_encrypted(main.THREADS_TOKEN_FILE)
            self.assertEqual(loaded_th["id"], "th-user-123")

    def test_telegram_webhook_authorization(self):
        # 1. Invalid secret in path
        resp = self.client.post("/telegram/webhook/wrong-secret", json={}, headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"})
        self.assertEqual(resp.status_code, 403)

        # 2. Invalid secret in header
        resp = self.client.post("/telegram/webhook/test-webhook-secret", json={}, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"})
        self.assertEqual(resp.status_code, 403)

        # 3. Valid secret
        resp = self.client.post("/telegram/webhook/test-webhook-secret", json={}, headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("app.main.telegram_api", new_callable=AsyncMock)
    @patch("app.main.generate_caption", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.get")
    async def test_telegram_message_intake_photo(self, mock_http_get, mock_gen_caption, mock_telegram_api):
        mock_telegram_api.side_effect = [
            {"message_id": 100},  # sendMessage ("Creating caption draft...")
            {"file_id": "f123", "file_path": "photos/file_0.jpg"},  # getFile
            {"message_id": 102},  # sendPhoto preview
        ]
        mock_gen_caption.return_value = "Meditation quote caption\n\n#meditation #peace"
        
        mock_http_response = MagicMock()
        mock_http_response.is_error = False
        mock_http_response.content = b"fake-jpg-binary-content"
        mock_http_get.return_value = mock_http_response

        message = {
            "chat": {"id": 123456789},
            "from": {"id": 123456789},
            "photo": [{"file_id": "small"}, {"file_id": "f123"}],
        }

        await main.handle_telegram_message(message)

        # Verify post created in SQLite DB
        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE telegram_user_id = '123456789'").fetchone()
        self.assertIsNotNone(post)
        self.assertEqual(post["status"], "AWAITING_APPROVAL")
        self.assertEqual(post["caption"], "Meditation quote caption\n\n#meditation #peace")
        conn.close()

    @patch("app.main.telegram_api", new_callable=AsyncMock)
    async def test_telegram_callback_cancel_and_edit(self, mock_telegram_api):
        # Insert a draft post
        conn = database()
        conn.execute(
            "INSERT INTO posts (id, telegram_chat_id, telegram_user_id, media_name, mime_type, caption, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("post-1", "123456789", "123456789", "post-1.jpg", "image/jpeg", "Draft caption", "AWAITING_APPROVAL"),
        )
        conn.commit()
        conn.close()

        # 1. Edit callback
        callback_edit = {
            "id": "cb1",
            "from": {"id": 123456789},
            "message": {"chat": {"id": 123456789}},
            "data": "edit:post-1",
        }
        await main.handle_telegram_callback(callback_edit)
        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE id = 'post-1'").fetchone()
        self.assertEqual(post["awaiting_edit"], 1)
        conn.close()

        # Send text to update edit
        msg_text = {
            "chat": {"id": 123456789},
            "from": {"id": 123456789},
            "text": "New updated caption #peace",
        }
        await main.handle_telegram_message(msg_text)
        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE id = 'post-1'").fetchone()
        self.assertEqual(post["awaiting_edit"], 0)
        self.assertEqual(post["caption"], "New updated caption #peace")
        self.assertEqual(post["status"], "AWAITING_APPROVAL")
        conn.close()

        # 2. Cancel callback
        callback_cancel = {
            "id": "cb2",
            "from": {"id": 123456789},
            "message": {"chat": {"id": 123456789}},
            "data": "cancel:post-1",
        }
        await main.handle_telegram_callback(callback_cancel)
        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE id = 'post-1'").fetchone()
        self.assertEqual(post["status"], "CANCELLED")
        conn.close()

    @patch("app.main.telegram_api", new_callable=AsyncMock)
    @patch("app.main.publish_to_instagram", new_callable=AsyncMock)
    @patch("app.main.publish_to_facebook_page", new_callable=AsyncMock)
    @patch("app.main.publish_to_threads", new_callable=AsyncMock)
    async def test_telegram_callback_approve_multiplatform(self, mock_th, mock_fb, mock_ig, mock_tg):
        # Save tokens for all 3 platforms
        save_encrypted(main.TOKEN_FILE, {"access_token": "ig-tok", "user_id": "ig-123"})
        save_encrypted(main.FACEBOOK_TOKEN_FILE, {"access_token": "fb-tok", "id": "fb-123", "name": "Test Page"})
        save_encrypted(main.THREADS_TOKEN_FILE, {"access_token": "th-tok", "user_id": "th-123"})

        mock_ig.return_value = "ig-post-888"
        mock_fb.return_value = "fb-post-999"
        mock_th.return_value = "th-post-777"

        # Insert draft
        conn = database()
        conn.execute(
            "INSERT INTO posts (id, telegram_chat_id, telegram_user_id, media_name, mime_type, caption, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("post-approve", "123456789", "123456789", "img.jpg", "image/jpeg", "Caption", "AWAITING_APPROVAL"),
        )
        conn.commit()
        conn.close()

        callback_approve = {
            "id": "cb_app",
            "from": {"id": 123456789},
            "message": {"chat": {"id": 123456789}},
            "data": "approve:post-approve",
        }
        await main.handle_telegram_callback(callback_approve)

        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE id = 'post-approve'").fetchone()
        self.assertEqual(post["status"], "PUBLISHED")
        self.assertEqual(post["instagram_media_id"], "ig-post-888")
        self.assertEqual(post["facebook_post_id"], "fb-post-999")
        self.assertEqual(post["threads_media_id"], "th-post-777")
        conn.close()

        # Verify telegram notification was called
        mock_tg.assert_called()

    @patch("httpx.AsyncClient.get")
    async def test_token_refresh(self, mock_http_get):
        save_encrypted(main.TOKEN_FILE, {"access_token": "old-ig-token"})
        save_encrypted(main.THREADS_TOKEN_FILE, {"access_token": "old-th-token"})

        # Mock refresh responses
        mock_response = MagicMock()
        mock_response.is_error = False
        mock_response.json.return_value = {"access_token": "new-refreshed-token", "expires_in": 5184000}
        mock_http_get.return_value = mock_response

        # Test Instagram refresh
        ig_res = await main.refresh_instagram_token()
        self.assertTrue(ig_res["ok"])
        loaded_ig = load_encrypted(main.TOKEN_FILE)
        self.assertEqual(loaded_ig["access_token"], "new-refreshed-token")

        # Test Threads refresh
        th_res = await main.refresh_threads_token()
        self.assertTrue(th_res["ok"])
        loaded_th = load_encrypted(main.THREADS_TOKEN_FILE)
        self.assertEqual(loaded_th["access_token"], "new-refreshed-token")

        # Test endpoint
        resp = self.client.get("/auth/refresh")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("app.main.telegram_api", new_callable=AsyncMock)
    @patch("app.main.publish_to_instagram", new_callable=AsyncMock)
    @patch("app.main.publish_to_facebook_page", new_callable=AsyncMock)
    async def test_telegram_callback_approve_partial_failure(self, mock_fb, mock_ig, mock_tg):
        # Save tokens for Instagram and Facebook
        save_encrypted(main.TOKEN_FILE, {"access_token": "ig-tok", "user_id": "ig-123"})
        save_encrypted(main.FACEBOOK_TOKEN_FILE, {"access_token": "fb-tok", "id": "fb-123", "name": "Test Page"})

        mock_ig.return_value = "ig-post-111"
        mock_fb.side_effect = RuntimeError("Facebook Page permissions error")

        # Insert draft
        conn = database()
        conn.execute(
            "INSERT INTO posts (id, telegram_chat_id, telegram_user_id, media_name, mime_type, caption, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("post-partial", "123456789", "123456789", "img_partial.jpg", "image/jpeg", "Caption", "AWAITING_APPROVAL"),
        )
        conn.commit()
        conn.close()

        callback_approve = {
            "id": "cb_part",
            "from": {"id": 123456789},
            "message": {"chat": {"id": 123456789}},
            "data": "approve:post-partial",
        }
        await main.handle_telegram_callback(callback_approve)

        conn = database()
        post = conn.execute("SELECT * FROM posts WHERE id = 'post-partial'").fetchone()
        self.assertEqual(post["status"], "PARTIAL_SUCCESS")
        self.assertEqual(post["instagram_media_id"], "ig-post-111")
        self.assertIsNone(post["facebook_post_id"])
        conn.close()

    async def test_media_cleanup(self):
        # Create a test media file
        test_file = main.MEDIA_DIR / "cleanup_test.jpg"
        test_file.write_bytes(b"temp-data")
        self.assertTrue(test_file.exists())

        # Test delayed cleanup
        await main.delayed_cleanup_media("cleanup_test.jpg", delay_seconds=0.01)
        self.assertFalse(test_file.exists())


if __name__ == "__main__":
    unittest.main()

