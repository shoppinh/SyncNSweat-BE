import base64
import hashlib
import secrets
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings
from app.services.spotify_interceptor import SpotifyInterceptor, SpotifyTokenExpiredException


class SpotifyService:
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.api_base_url = "https://api.spotify.com/v1"
    
    def _create_interceptor(self) -> SpotifyInterceptor:
        """Create a new interceptor instance with token refresh callback."""
        return SpotifyInterceptor(refresh_token_callback=self.refresh_access_token)
    
    def _make_api_call_with_interceptor(
        self,
        method: str,
        url: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an API call using the interceptor for automatic token handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full API endpoint URL
            access_token: Current Spotify access token
            refresh_token: Spotify refresh token (optional)
            expires_at: Unix timestamp when token expires (optional)
            params: URL query parameters
            data: Form data for POST requests
            json_data: JSON body for POST requests
            
        Returns:
            Parsed JSON response
        """
        interceptor = self._create_interceptor()
        try:
            return interceptor.make_request(
                method=method,
                url=url,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                params=params,
                data=data,
                json_data=json_data,
            )
        except SpotifyTokenExpiredException as e:
            # If token refresh fails, raise an error
            raise Exception(f"Token refresh failed: {str(e)}")
    
    def get_access_token_with_interceptor(
        self, code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token using interceptor with PKCE.
        
        Returns a dict with access_token, refresh_token, and expires_in
        """
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        token_response = response.json()
        
        # Store expiration timestamp if expires_in is provided
        if "expires_in" in token_response:
            import time
            token_response["expires_at"] = time.time() + token_response["expires_in"]
        
        return token_response
    

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        return code_verifier, code_challenge

    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple[str, str]:
        """
        Get the Spotify authorization URL with PKCE.
        Returns (auth_url, code_verifier)
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
    
    async def get_user_profile(self, access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[float] = None) -> Dict[str, Any]:
        """
        Get the user's Spotify profile with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/me",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
    
    async def get_user_playlists(self, access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[float] = None, limit: int = 50) -> Dict[str, Any]:
        """
        Get the user's playlists with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/me/playlists",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            params={"limit": limit}
        )
    
    async def create_playlist(
        self,
        access_token: str,
        user_id: str,
        name: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        description: str = "",
        public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new playlist with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="POST",
            url=f"{self.api_base_url}/users/{user_id}/playlists",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            json_data={
                "name": name,
                "description": description,
                "public": public
            }
        )
    
    async def add_tracks_to_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: List[str],
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Add tracks to a playlist with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="POST",
            url=f"{self.api_base_url}/playlists/{playlist_id}/tracks",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            json_data={"uris": track_uris}
        )
    
    async def get_seed_tracks(self, access_token: str, genres: List[str], fitness_goal: str,
                            refresh_token: Optional[str] = None, 
                            expires_at: Optional[float] = None) -> List[str]:
        """Get seed tracks based on genres and fitness goal with automatic token refresh."""
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
        params: Dict[str, Any] = {
            "seed_genres": ",".join(selected_genres[:5]),
            "limit": 2,  # Get 2 tracks to use as seeds
        }
        
        response_data = self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/recommendations",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            params=params
        )
            
        tracks = response_data.get("tracks", [])
        return [track["id"] for track in tracks]


    async def create_workout_playlist(self, access_token: str, track_uris: List[str], 
                                    fitness_goal: str, user_id: str, 
                                    refresh_token: Optional[str] = None, 
                                    expires_at: Optional[float] = None) -> Dict[str, Any]:
        """Create a new playlist with the recommended tracks."""
        # Get user profile for display name
        user_profile = await self.get_user_profile(access_token, refresh_token, expires_at)
        display_name = user_profile.get("display_name", "User")
        
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
            refresh_token=refresh_token,
            expires_at=expires_at
        )

        if not playlist or "id" not in playlist:
            raise Exception(f"Failed to create playlist: {playlist}")

        # Add tracks to the playlist
        result = await self.add_tracks_to_playlist(
            access_token=access_token,
            playlist_id=playlist["id"],
            track_uris=track_uris,
            refresh_token=refresh_token,
            expires_at=expires_at
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

    async def get_current_user_top_tracks(self, access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[float] = None) -> Dict[str, Any]:
        """Get the user's top tracks with automatic token refresh."""
        try:
            return self._make_api_call_with_interceptor(
                method="GET",
                url=f"{self.api_base_url}/me/top/tracks",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )
        except Exception:
            return {"items": []}
        
    
    
    async def get_current_user_top_artists(self, access_token: str, refresh_token: Optional[str] = None, expires_at: Optional[float] = None) -> Dict[str, Any]:
        """Get the user's top artists with automatic token refresh."""
        try:
            return self._make_api_call_with_interceptor(
                method="GET",
                url=f"{self.api_base_url}/me/top/artists",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )
        except Exception:
            return {"items": []}
        
    async def search_tracks(self, access_token: str, search_query: str, refresh_token: Optional[str] = None, expires_at: Optional[float] = None) -> Dict[str, Any]:
        """Search for tracks with automatic token refresh."""
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/search",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            params={"q": search_query, "type": "track"}
        )



