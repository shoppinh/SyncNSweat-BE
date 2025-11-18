import unittest
from typing import Any, Dict

from app.services import preferences as preferences_service


class FakeQuery:
    def __init__(self, result=None):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class FakeDB:
    def __init__(self, existing=None):
        # existing is the result that FakeQuery.first() should return
        self._existing = existing
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, model):
        return FakeQuery(self._existing)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


class TestPreferencesService(unittest.TestCase):
    def test_update_spotify_tokens_creates_preferences(self):
        fake_db = FakeDB(existing=None)
        token_data: Dict[str, Any] = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        prefs = preferences_service.update_spotify_tokens(fake_db, profile_id=123, token_data=token_data)

        # The returned object should have the token fields set
        self.assertTrue(prefs.spotify_connected)
        self.assertEqual(prefs.spotify_data.get("access_token"), "new_access")
        self.assertEqual(prefs.spotify_data.get("refresh_token"), "new_refresh")
        self.assertTrue(fake_db.committed)

    def test_update_spotify_tokens_updates_existing(self):
        # Create a fake existing preferences-like object
        class ExistingPrefs:
            def __init__(self):
                self.profile_id = 123
                self.spotify_connected = False
                self.spotify_data = {}

        existing = ExistingPrefs()
        fake_db = FakeDB(existing=existing)
        token_data = {"access_token": "a2", "refresh_token": "r2"}

        prefs = preferences_service.update_spotify_tokens(fake_db, profile_id=123, token_data=token_data)

        self.assertTrue(prefs.spotify_connected)
        self.assertEqual(prefs.spotify_data.get("access_token"), "a2")
        self.assertEqual(prefs.spotify_data.get("refresh_token"), "r2")
        self.assertTrue(fake_db.committed)


if __name__ == "__main__":
    unittest.main()
