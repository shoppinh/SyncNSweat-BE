import base64
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings


class SpotifyService:
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.api_base_url = "https://api.spotify.com/v1"

    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get the Spotify authorization URL.
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "user-read-private user-read-email user-library-read user-library-modify user-top-read user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public playlist-modify-private",
        }
        if state:
            params["state"] = state

        auth_url = f"{self.auth_url}?" + "&".join(
            [f"{k}={v}" for k, v in params.items()]
        )
        return auth_url

    def get_access_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        """
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        response = requests.post(self.token_url, headers=headers, data=data)
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token.
        """
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

        response = requests.post(self.token_url, headers=headers, data=data)
        return response.json()

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get the user's Spotify profile.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(f"{self.api_base_url}/me", headers=headers)
        return response.json()

    async def get_user_playlists(
        self, access_token: str, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get the user's playlists.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(
            f"{self.api_base_url}/me/playlists?limit={limit}", headers=headers
        )
        return response.json()

    async def create_playlist(
        self,
        access_token: str,
        user_id: str,
        name: str,
        description: str = "",
        public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new playlist.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data = {"name": name, "description": description, "public": public}

        response = requests.post(
            f"{self.api_base_url}/users/{user_id}/playlists", headers=headers, json=data
        )
        return response.json()

    async def add_tracks_to_playlist(
        self, access_token: str, playlist_id: str, track_uris: List[str]
    ) -> Dict[str, Any]:
        """
        Add tracks to a playlist.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data = {"uris": track_uris}

        response = requests.post(
            f"{self.api_base_url}/playlists/{playlist_id}/tracks",
            headers=headers,
            json=data,
        )
        return response.json()

    async def get_seed_tracks(
        self, access_token: str, genres: list, fitness_goal: str
    ) -> list:
        """Get seed tracks based on genres and fitness goal."""
        headers = {"Authorization": f"Bearer {access_token}"}

        # Map fitness goals to appropriate genres
        fitness_genres = {
            "weight_loss": ["electronic", "dance", "pop"],
            "muscle_gain": ["hip-hop", "rock", "metal"],
            "flexibility": ["ambient", "chill", "classical"],
        }

        # Combine workout-specific genres with user preferences
        selected_genres = fitness_genres.get(fitness_goal, [])
        if genres:
            selected_genres.extend([g for g in genres if g not in selected_genres])
        selected_genres = selected_genres[:5]  # Spotify allows max 5 seed genres

        # Get recommendations based on genres to use as seeds
        params = {
            "seed_genres": ",".join(selected_genres[:5]),
            "limit": 2,  # Get 2 tracks to use as seeds
        }

        response = requests.get(
            f"{self.api_base_url}/recommendations", headers=headers, params=params
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get seed tracks: {response.json()}")

        tracks = response.json().get("tracks", [])
        return [track["id"] for track in tracks]

    async def create_workout_playlist(
        self, access_token: str, track_uris: list, fitness_goal: str, user_id: str
    ) -> Dict[str, Any]:
        """Create a new playlist with the recommended tracks."""
        # Get user profile for display name
        user_profile = await self.get_user_profile(access_token)
        display_name = (user_profile or {}).get("display_name", "User")

        # Create playlist name and description
        fitness_names = {
            "weight_loss": "Fat Burn",
            "muscle_gain": "Muscle Builder",
            "flexibility": "Flexibility Flow",
        }
        playlist_name = (
            f"{fitness_names.get(fitness_goal, 'Workout')} for {display_name}"
        )
        description = (
            f"Custom {fitness_goal.title()} workout playlist created by SyncNSweat"
        )

        # Create the playlist
        playlist = await self.create_playlist(
            access_token=access_token,
            user_id=user_id,
            name=playlist_name,
            description=description,
            public=False,  # Keep private by default
        )

        if not playlist or "id" not in playlist:
            raise Exception(f"Failed to create playlist: {playlist}")

        # Add tracks to the playlist
        result = await self.add_tracks_to_playlist(
            access_token=access_token, playlist_id=playlist["id"], track_uris=track_uris
        )

        if not result or "snapshot_id" not in result:
            raise Exception(f"Failed to add tracks to playlist: {result}")

        # Return playlist details
        return {
            "id": playlist["id"],
            "name": playlist_name,
            "external_url": (playlist.get("external_urls") or {}).get("spotify"),
            "image_url": playlist.get("images")[0]["url"]
            if playlist.get("images")
            else None,
        }

    async def get_current_user_top_tracks(self, access_token: str) -> dict:
        """Get the user's top tracks."""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(
                f"{self.api_base_url}/me/top/tracks", headers=headers
            )
            return {"items": response.json().get("items", [])}
        except Exception as e:
            return {"items": []}

    async def get_current_user_top_artists(self, access_token: str) -> dict:
        """Get the user's top artists."""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(
                f"{self.api_base_url}/me/top/artists", headers=headers
            )
            return {"items": response.json().get("items", [])}
        except Exception as e:
            return {"items": []}

    async def search_tracks(self, access_token: str, search_query: str) -> dict:
        """Search for tracks."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{self.api_base_url}/search",
            headers=headers,
            params={"q": search_query, "type": "track"},
        )
        return response.json()
