"""
Spotify API Interceptor for handling token expiration and automatic refresh.
This module provides a base interceptor that wraps Spotify API calls with
automatic token refresh capabilities.
"""

import requests
import time
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SpotifyTokenExpiredException(Exception):
    """Raised when a Spotify access token has expired."""
    pass


class SpotifyAPIError(Exception):
    """Raised when a Spotify API call fails."""
    pass


class SpotifyInterceptor:
    """
    Base interceptor for Spotify API calls that handles token expiration
    and automatic token refresh.
    """

    def __init__(
        self,
        refresh_token_callback: Callable[[str], Dict[str, Any]],
        persist_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the interceptor.
        
        Args:
            refresh_token_callback: A callable that takes a refresh_token and returns 
            a dict with new access_token and optionally expires_in
        """
        self.refresh_token_callback = refresh_token_callback
        # Optional callback used to persist token data to the application's
        # storage (for example update user Preferences). This keeps the
        # interceptor decoupled from the database layer and lets the caller
        # provide a closure that captures a DB session or service instance.
        self.persist_callback = persist_callback
        self.token_buffer_seconds = 300

    def is_token_expired(self, expires_at: Optional[float] = None) -> bool:
        """Check if a token is expired or about to expire."""
        if expires_at is None:
            return False
        
        current_time = time.time()
        time_until_expiry = expires_at - current_time
        return time_until_expiry < self.token_buffer_seconds

    def refresh_expired_token(
        self, refresh_token: str
    ) -> Optional[str]:
        """Refresh an expired token and return the new access token."""
        logger.warning("Attempting to refresh expired Spotify access token")
        
        try:
            token_data = self.refresh_token_callback(refresh_token)
            new_access_token = token_data.get("access_token")
            
            if new_access_token:
                # If the caller provided a persistence callback, call it with
                # the raw token_data. The callback is responsible for storing
                # access/refresh tokens and any expiry information.
                try:
                    if self.persist_callback:
                        # allow the callback to raise if persistence fails
                        self.persist_callback(token_data)
                except Exception:
                    logger.exception("Failed to persist refreshed Spotify token")

                logger.info("Successfully refreshed Spotify access token")
                return new_access_token
            
            logger.error("Token refresh failed: no access_token in response")
            return None
                
        except Exception as e:
            logger.error("Error refreshing Spotify token: %s", str(e))
            return None

    def _make_request_with_headers(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Execute HTTP request with provided headers."""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            )
            return response
        except requests.RequestException as e:
            logger.error("Request error for %s %s: %s", method, url, str(e))
            raise SpotifyAPIError(f"Spotify API request failed: {str(e)}")

    def intercept_request(
        self,
        method: str,
        url: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Execute a Spotify API request with automatic token refresh.
        
        Returns the response or raises SpotifyAPIError
        """
        current_token = access_token
        
        # Check if token is proactively expired
        if self.is_token_expired(expires_at) and refresh_token:
            logger.info("Token is about to expire. Refreshing proactively")
            new_token = self.refresh_expired_token(refresh_token)
            if new_token:
                current_token = new_token
            else:
                raise SpotifyTokenExpiredException("Failed to refresh token")
        
        # Set up headers with current access token
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {current_token}"
        }
        
        # Make the request
        response = self._make_request_with_headers(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json_data=json_data
        )
        
        # Handle 401 response with token refresh and retry
        if response.status_code == 401 and refresh_token:
            logger.info("Received 401 response. Attempting token refresh and retry")
            new_token = self.refresh_expired_token(refresh_token)
            
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = self._make_request_with_headers(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json_data=json_data
                )
        
        return response

    def make_request(
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
        Make a Spotify API request with automatic token handling.
        
        Returns parsed JSON response or error dict
        """
        response = self.intercept_request(
            method=method,
            url=url,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            params=params,
            data=data,
            json_data=json_data
        )
        
        try:
            return response.json()
        except ValueError:
            return {
                "error": "Invalid JSON response",
                "status_code": response.status_code
            }
