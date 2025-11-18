import random
from typing import List, Dict, Any, Optional
from app.services.spotify import SpotifyService

class PlaylistSelectorService:
    """
    Service for selecting playlists based on workout type and user preferences.
    """
    
    def __init__(self):
        self.spotify_service = SpotifyService()
        self.energy_map = {
            "Full Body": 0.8,
            "Upper Body": 0.7,
            "Lower Body": 0.8,
            "Push": 0.7,
            "Pull": 0.7,
            "Legs": 0.8,
            "Chest": 0.7,
            "Back": 0.7,
            "Shoulders": 0.7,
            "Arms": 0.6,
            "Core": 0.6
        }
        
        self.tempo_map = {
            "slow": 100,
            "medium": 130,
            "fast": 160
        }
    
    def select_playlist_for_workout(
        self,
        access_token: str,
        workout_focus: str,
        music_genres: List[str],
        music_tempo: str,
        recently_used_playlists: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Select a playlist for a workout based on the workout focus and user preferences.
        
        Args:
            access_token: Spotify access token
            workout_focus: The focus of the workout (e.g., "Upper Body", "Push")
            music_genres: List of user's preferred music genres
            music_tempo: User's preferred music tempo (e.g., "slow", "medium", "fast")
            recently_used_playlists: List of recently used playlist IDs to avoid
            
        Returns:
            A dictionary with playlist information
        """
        if not recently_used_playlists:
            recently_used_playlists = []
        
        # Map workout focus to energy level
        # Get energy level and tempo based on workout focus and user preferences

        target_params = self.calculate_target_params(workout_focus, music_tempo)
        target_energy = target_params["target_energy"]
        target_tempo = target_params["target_tempo"]
        
        # Get recommendations from Spotify
        recommendations = self.spotify_service.get_recommendations(
            access_token=access_token,
            seed_genres=music_genres[:2] if music_genres else ["workout", "pop"],
            limit=20,
            target_energy=target_energy,
            target_tempo=target_tempo
        )
        
        # Check if we got any recommendations
        if "tracks" not in recommendations or not recommendations["tracks"]:
            # Fallback to user's playlists
            user_playlists = self.spotify_service.get_user_playlists(access_token)
            
            if "items" not in user_playlists or not user_playlists["items"]:
                # No playlists found, return a default response
                return {
                    "id": None,
                    "name": "No playlist found",
                    "description": "Please connect your Spotify account and add some playlists",
                    "external_url": None,
                    "image_url": None
                }
            
            # Filter out recently used playlists
            available_playlists = [
                p for p in user_playlists["items"]
                if p["id"] not in recently_used_playlists
            ]
            
            if not available_playlists:
                # If all playlists were recently used, just use any playlist
                available_playlists = user_playlists["items"]
            
            # Select a random playlist
            playlist = random.choice(available_playlists)
            
            return {
                "id": playlist["id"],
                "name": playlist["name"],
                "description": playlist.get("description", ""),
                "external_url": playlist["external_urls"]["spotify"] if "external_urls" in playlist else None,
                "image_url": playlist["images"][0]["url"] if playlist.get("images") else None
            }
        
        # Create a playlist from the recommendations
        user_profile = self.spotify_service.get_user_profile(access_token)
        user_id = user_profile["id"]
        
        # Create a name for the playlist based on the workout focus
        playlist_name = f"{workout_focus} Workout Mix"
        playlist_description = f"A {music_tempo} tempo playlist for your {workout_focus.lower()} workout"
        
        # Create the playlist
        playlist = self.spotify_service.create_playlist(
            access_token=access_token,
            user_id=user_id,
            name=playlist_name,
            description=playlist_description
        )
        
        # Add tracks to the playlist
        track_uris = [track["uri"] for track in recommendations["tracks"]]
        self.spotify_service.add_tracks_to_playlist(
            access_token=access_token,
            playlist_id=playlist["id"],
            track_uris=track_uris
        )
        
        return {
            "id": playlist["id"],
            "name": playlist["name"],
            "description": playlist["description"],
            "external_url": playlist["external_urls"]["spotify"] if "external_urls" in playlist else None,
            "image_url": playlist["images"][0]["url"] if playlist.get("images") else None
        }
    
    def get_playlist_recommendations(
        self,
        access_token: str,
        music_genres: List[str],
        music_tempo: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get playlist recommendations based on user preferences.
        
        Args:
            access_token: Spotify access token
            music_genres: List of user's preferred music genres
            music_tempo: User's preferred music tempo (e.g., "slow", "medium", "fast")
            limit: Number of playlists to return
            
        Returns:
            A list of playlist dictionaries
        """
        # Map tempo to target tempo (BPM)

        
        target_params = self.calculate_target_params(None, music_tempo)
        target_tempo = target_params["target_tempo"]
        
        # Get recommendations from Spotify
        recommendations = self.spotify_service.get_recommendations(
            access_token=access_token,
            seed_genres=music_genres[:2] if music_genres else ["workout", "pop"],
            limit=limit * 4,  # Get more tracks to create multiple playlists
            target_tempo=target_tempo
        )
        
        if "tracks" not in recommendations or not recommendations["tracks"]:
            # Fallback to user's playlists
            user_playlists = self.spotify_service.get_user_playlists(access_token, limit=limit)
            
            if "items" not in user_playlists or not user_playlists["items"]:
                # No playlists found, return an empty list
                return []
            
            # Return user's playlists
            return [
                {
                    "id": playlist["id"],
                    "name": playlist["name"],
                    "description": playlist.get("description", ""),
                    "external_url": playlist["external_urls"]["spotify"] if "external_urls" in playlist else None,
                    "image_url": playlist["images"][0]["url"] if playlist.get("images") else None
                }
                for playlist in user_playlists["items"][:limit]
            ]
        
        # Group tracks into playlists
        tracks_per_playlist = len(recommendations["tracks"]) // limit
        playlists = []
        
        for i in range(min(limit, len(recommendations["tracks"]) // tracks_per_playlist)):
            # Create a name for the playlist
            playlist_name = f"Workout Mix {i+1}"
            
            # Get tracks for this playlist
            start_idx = i * tracks_per_playlist
            end_idx = start_idx + tracks_per_playlist
            playlist_tracks = recommendations["tracks"][start_idx:end_idx]
            
            # Create a description based on the tracks
            artists = set()
            for track in playlist_tracks:
                for artist in track["artists"]:
                    artists.add(artist["name"])
            
            artists_str = ", ".join(list(artists)[:3])
            if len(artists) > 3:
                artists_str += f" and {len(artists) - 3} more"
            
            playlist_description = f"A workout mix featuring {artists_str}"
            
            playlists.append({
                "id": f"recommendation_{i}",
                "name": playlist_name,
                "description": playlist_description,
                "external_url": None,
                "image_url": None,
                "preview_tracks": [
                    {
                        "name": track["name"],
                        "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                        "album": track["album"]["name"] if "album" in track else "Unknown"
                    }
                    for track in playlist_tracks[:3]  # Preview first 3 tracks
                ]
            })
        
        return playlists

    def calculate_target_params(
    self,
    workout_focus: Optional[str] = None,
    music_tempo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """        Calculate target parameters for recommendations based on workout type and music tempo.
        """
        # Map workout type to energy level
        target_energy = self.energy_map.get(workout_focus, 0.7)
        target_tempo = self.tempo_map.get(music_tempo, 130)

        return {
            "target_energy": target_energy,
            "target_tempo": target_tempo
        }
        
