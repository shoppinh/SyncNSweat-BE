import base64
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
import requests

from app.core.config import settings
from app.services.preferences import PreferencesService
from app.services.spotify_interceptor import SpotifyInterceptor, SpotifyTokenExpiredException
from app.models.profile import Profile
from app.models.preferences import Preferences


class SpotifyService:
    def __init__(
        self,
        db: Optional[Session] = None,
        profile: Optional[Profile] = None,
        preferences: Optional[Preferences] = None
    ):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.api_base_url = "https://api.spotify.com/v1"
        self.db = db
        self.profile = profile
        self.preferences = preferences
    
    def _create_interceptor(self) -> SpotifyInterceptor:
        """Create a new interceptor instance with token refresh and persistence callbacks."""
        return SpotifyInterceptor(
            refresh_token_callback=self.refresh_access_token,
            persist_callback=self.persist_callback,
        )

    def persist_callback(self, token_data: Dict[str, Any]) -> None:
        """Persist refreshed token data to the database (e.g. update Preferences)."""
        # Persist refreshed token data to the DB and update in-memory preferences.
        # Do not raise from this callback — keep it best-effort and fail silently
        # to avoid breaking the caller flow when persistence fails.
        if not (self.profile and self.db):
            return

        try:
            preferences_service = PreferencesService(self.db)
            updated_pref = preferences_service.update_spotify_tokens(
                profile_id=getattr(self.profile, "id"),
                token_data=token_data,
            )

            # `update_spotify_tokens` commits and refreshes the returned instance
            # when using the same Session. Still defensively ensure we have a
            # fresh ORM object in this session.
            try:
                # If the returned object is attached to a different session or
                # needs refreshing, try to refresh it in our session.
                if hasattr(self.db, "refresh"):
                    self.db.refresh(updated_pref)
            except Exception:
                # If refresh fails, attempt to re-query by profile_id as a fallback.
                try:
                    updated_pref = (
                        self.db.query(Preferences)
                        .filter(Preferences.profile_id == self.profile.id)
                        .first()
                    )
                except Exception:
                    updated_pref = None

            if updated_pref is not None:
                self.preferences = updated_pref
        except Exception as e:
            print(f"Error persisting refreshed tokens: {str(e)}")
            # Swallow exceptions here — persistence failure should not crash
            # the interceptor flow. Operators can monitor logs to detect issues.
            return
    
    def _make_api_call_with_interceptor(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
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
        input_access_token = access_token or (self.preferences.spotify_data.get("access_token") if self.preferences else None) 
        input_refresh_token = refresh_token or (self.preferences.spotify_data.get("refresh_token") if self.preferences else None)
        input_expires_at = expires_at or (self.preferences.spotify_data.get("expires_at") if self.preferences else None)
        if not input_access_token:
            raise Exception("Access token is required for API call")
        try:
            return interceptor.make_request(
                method=method,
                url=url,
                access_token=input_access_token,
                refresh_token=input_refresh_token,
                expires_at=input_expires_at,
                params=params,
                data=data,
                json_data=json_data,
            )
        except SpotifyTokenExpiredException as e:
            # If token refresh fails, raise an error
            raise Exception(f"Token refresh failed: {str(e)}")

    def make_api_call(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Public wrapper around the interceptor-backed API call.

        This keeps higher-level services from reaching into protected internals
        while still leveraging the interceptor's token refresh behavior.
        """
        return self._make_api_call_with_interceptor(
            method=method,
            url=url,
            params=params,
            data=data,
            json_data=json_data,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
    
    def get_access_token_with_interceptor(
        self, code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token using interceptor.
        
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
    


    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get the Spotify authorization URL .
        Returns (auth_url, code_verifier)
        """
        
        params: Dict[str, Any] = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "user-read-private user-read-email user-library-read user-library-modify user-top-read user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-public playlist-modify-private user-read-recently-played",
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
    
    async def get_user_profile(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None, expires_at: Optional[float] = None) -> Dict[str, Any]:
        """
        Get the user's Spotify profile with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/me",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
    
    async def get_user_playlists(self, limit: int = 50) -> Dict[str, Any]:
        """
        Get the user's playlists with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/me/playlists",
            params={"limit": limit}
        )
    
    async def create_playlist(
        self,
        user_id: str,
        name: str,
        description: str = "",
        public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new playlist with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="POST",
            url=f"{self.api_base_url}/users/{user_id}/playlists",
            json_data={
                "name": name,
                "description": description,
                "public": public
            }
        )
    
    async def add_tracks_to_playlist(
        self,
        playlist_id: str,
        track_uris: List[str],
    ) -> Dict[str, Any]:
        """
        Add tracks to a playlist with automatic token refresh.
        """
        return self._make_api_call_with_interceptor(
            method="POST",
            url=f"{self.api_base_url}/playlists/{playlist_id}/tracks",
            json_data={"uris": track_uris}
        )
    
    async def get_seed_tracks(self,  genres: List[str], fitness_goal: str) -> List[str]:
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
            params=params
        )
            
        tracks = response_data.get("tracks", [])
        return [track["id"] for track in tracks]


    async def create_workout_playlist(self,  track_uris: List[str], 
                                    fitness_goal: str, user_id: str, 
                                    ) -> Dict[str, Any]:
        """Create a new playlist with the recommended tracks."""
        # Get user profile for display name
        user_profile = await self.get_user_profile()
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
            user_id=user_id,
            name=playlist_name,
            description=description,
            public=False,  # Keep private by default
        )

        if not playlist or "id" not in playlist:
            raise Exception(f"Failed to create playlist: {playlist}")

        # Add tracks to the playlist
        result = await self.add_tracks_to_playlist(
            playlist_id=playlist["id"],
            track_uris=track_uris,
        )

        if not result or "snapshot_id" not in result:
            raise Exception(f"Failed to add tracks to playlist: {result}")

        # Return playlist details
        return {
            "id": playlist["id"],
            "name": playlist_name,
            "external_url": playlist.get("external_urls", {}).get("spotify", ""),
            "image_url":playlist.get("images", [])[0]["url"] or None
            if playlist.get("images")
            else None,
        }

    async def get_current_user_top_tracks(self) -> Dict[str, Any]:
        """Get the user's top tracks with automatic token refresh."""
        try:
            return self._make_api_call_with_interceptor(
                method="GET",
                url=f"{self.api_base_url}/me/top/tracks",
            )
        except Exception:
            return {"items": []}
        
    
    
    async def get_current_user_top_artists(self) -> Dict[str, Any]:
        """Get the user's top artists with automatic token refresh."""
        try:
            return self._make_api_call_with_interceptor(
                method="GET",
                url=f"{self.api_base_url}/me/top/artists",
            )
        except Exception:
            return {"items": []}
        
    async def search_tracks(self, search_query: str) -> Dict[str, Any]:
        """Search for tracks with automatic token refresh."""
        return self._make_api_call_with_interceptor(
            method="GET",
            url=f"{self.api_base_url}/search",
            params={"q": search_query, "type": "track"}
        )



